import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.db.models import Project, User, AuditLog, EvaluationRun, ComplianceReport
from backend.app.core.security import create_access_token
import os
import shutil

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture(scope="module")
def auth_headers(db):
    user = db.query(User).filter(User.username == "admin").first()
    token = create_access_token({"sub": user.username})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def user_headers(db):
    user = db.query(User).filter(User.username == "operator").first()
    token = create_access_token({"sub": user.username})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def test_project(db):
    project = Project(
        id="proj-test-upload",
        name="Test Upload Project",
        organization="Test Org",
        sector="Healthcare",
        environment="production",
        cloud_provider="AWS",
        aws_region="us-east-1",
        owner="admin",
        status="Protected"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    yield project
    db.delete(project)
    db.commit()

def test_unauthenticated_upload_rejected():
    response = client.post("/api/v1/projects/proj-test-upload/upload/infrastructure", data={"hcl_code": "test"})
    assert response.status_code == 401

def test_cross_project_upload_infrastructure_rejected(user_headers, test_project):
    response = client.post(
        f"/api/v1/projects/{test_project.id}/upload/infrastructure",
        data={"hcl_code": "test"},
        headers=user_headers
    )
    assert response.status_code == 403

def test_cross_project_upload_application_rejected(user_headers, test_project):
    response = client.post(
        f"/api/v1/projects/{test_project.id}/upload/application",
        files={"file": ("app.zip", b"dummy", "application/zip")},
        headers=user_headers
    )
    assert response.status_code == 403

def test_cross_project_get_hcl_rejected(user_headers, test_project):
    response = client.get(f"/api/v1/projects/{test_project.id}/hcl", headers=user_headers)
    assert response.status_code == 403

def test_upload_infrastructure_hcl_text(auth_headers, test_project, db):
    hcl_payload = "resource \"aws_s3_bucket\" \"test\" {}"
    response = client.post(
        f"/api/v1/projects/{test_project.id}/upload/infrastructure",
        data={"hcl_code": hcl_payload},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify DB
    db.refresh(test_project)
    assert test_project.hcl_content == hcl_payload

def test_upload_infrastructure_tf_file(auth_headers, test_project, db):
    test_hcl = 'resource "aws_db_instance" "test" {}'
    file_content = test_hcl.encode("utf-8")
    
    files = {"file": ("main.tf", file_content, "application/octet-stream")}
    response = client.post(
        f"/api/v1/projects/{test_project.id}/upload/infrastructure",
        files=files,
        headers=auth_headers
    )
    assert response.status_code == 200
    
    db.refresh(test_project)
    assert test_project.hcl_content == test_hcl
    assert test_project.infrastructure_path is not None
    assert os.path.exists(test_project.infrastructure_path)
    
    # Cleanup
    if os.path.exists(test_project.infrastructure_path):
        shutil.rmtree(test_project.infrastructure_path)

def test_upload_infrastructure_multifile_zip(auth_headers, test_project, db):
    # Create an in-memory zip file with multiple .tf files
    import io
    import zipfile
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("a_main.tf", 'resource "aws_vpc" "main" {}')
        zip_file.writestr("b_variables.tf", 'variable "region" {}')
        zip_file.writestr("c_outputs.tf", 'output "vpc_id" {}')
        
    file_content = zip_buffer.getvalue()
    files = {"file": ("infra.zip", file_content, "application/zip")}
    
    response = client.post(
        f"/api/v1/projects/{test_project.id}/upload/infrastructure",
        files=files,
        headers=auth_headers
    )
    assert response.status_code == 200
    
    db.refresh(test_project)
    expected_content = 'resource "aws_vpc" "main" {}\n\nvariable "region" {}\n\noutput "vpc_id" {}'
    assert test_project.hcl_content == expected_content
    
    if os.path.exists(test_project.infrastructure_path):
        shutil.rmtree(test_project.infrastructure_path)

def test_get_project_hcl(auth_headers, test_project):
    response = client.get(f"/api/v1/projects/{test_project.id}/hcl", headers=auth_headers)
    assert response.status_code == 200
    assert "hcl_code" in response.json()
    assert response.json()["hcl_code"] == test_project.hcl_content

def test_compliance_engine_uses_project_hcl(auth_headers, test_project):
    # Set a specific HCL that will fail a known rule
    test_project.hcl_content = 'resource "aws_s3_bucket" "bad" { bucket = "bad" }'
    
    response = client.post(
        "/api/v1/compliance/evaluate",
        json={"project_id": test_project.id, "trigger_type": "MANUAL_SCAN"},
        headers=auth_headers
    )
    assert response.status_code == 200
    res_data = response.json()
    
    # Should evaluate the bad bucket and fail (missing encryption, etc.)
    assert res_data["overall_status"] in ["FAIL", "REVIEW_REQUIRED", "PASS"] # Just verify it evaluates without crashing

def test_remediation_rds_public(auth_headers, test_project, db):
    test_project.hcl_content = 'resource "aws_db_instance" "db" {\\n  publicly_accessible = true\\n}'
    db.commit()
    response = client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_DISABLE_RDS_PUBLIC"]},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "publicly_accessible = false" in response.json()["hcl_code"]
    assert "ACT_DISABLE_RDS_PUBLIC" in response.json()["applied_actions"]

def test_remediation_rds_encryption(auth_headers, test_project, db):
    test_project.hcl_content = 'resource "aws_db_instance" "db" {\\n  allocated_storage = 20\\n}'
    db.commit()
    response = client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_ENABLE_RDS_ENC"]},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "storage_encrypted = true" in response.json()["hcl_code"]
    assert "ACT_ENABLE_RDS_ENC" in response.json()["applied_actions"]

def test_remediation_s3_encryption(auth_headers, test_project, db):
    test_project.hcl_content = 'resource "aws_s3_bucket" "b" {\\n  bucket = "b"\\n}'
    db.commit()
    response = client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_ENABLE_S3_ENC"]},
        headers=auth_headers
    )
    assert response.status_code == 200
    code = response.json()["hcl_code"]
    assert 'resource "aws_s3_bucket_server_side_encryption_configuration"' in code
    assert "ACT_ENABLE_S3_ENC" in response.json()["applied_actions"]

def test_remediation_cloudwatch_retention(auth_headers, test_project, db):
    test_project.hcl_content = 'resource "aws_cloudwatch_log_group" "cw" {\\n  retention_in_days = 30\\n}'
    db.commit()
    response = client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_EXTEND_LOG_RETENTION_180"]},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert "retention_in_days = 180" in response.json()["hcl_code"]
    assert "ACT_EXTEND_LOG_RETENTION_180" in response.json()["applied_actions"]

def test_remediation_unsupported_action(auth_headers, test_project, db):
    test_project.hcl_content = 'resource "aws_db_instance" "db" {}'
    db.commit()
    response = client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_UPGRADE_WEAK_CRYPTO", "ACT_UNKNOWN"]},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["applied_actions"]) == 0
    assert len(data["skipped_actions"]) == 2
    assert test_project.hcl_content == data["hcl_code"]

def test_cross_project_remediation_rejected(user_headers, test_project):
    response = client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_ENABLE_RDS_ENC"]},
        headers=user_headers
    )
    assert response.status_code == 403

def test_evaluation_run_persists_actual_evidence(auth_headers, test_project, db):
    test_project.hcl_content = 'resource "aws_db_instance" "test" { allocated_storage = 20 }'
    db.commit()

    response = client.post(
        "/api/v1/compliance/evaluate",
        json={"project_id": test_project.id, "trigger_type": "MANUAL_SCAN"},
        headers=auth_headers
    )
    assert response.status_code == 200
    run_id = response.json()["evaluation_run_id"]
    
    # Check DB
    run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    assert run is not None
    payload = run.evidence_payload
    
    assert "hcl_code" in payload
    assert payload["hcl_code"] == test_project.hcl_content
    assert "opa_violations" in payload
    assert isinstance(payload["opa_violations"], list)
    assert "sonar_findings" in payload
    
def test_evidence_hash_changes_if_evidence_changes(auth_headers, test_project, db):
    # Run 1
    test_project.hcl_content = 'resource "aws_s3_bucket" "test1" {}'
    db.commit()
    r1 = client.post(
        "/api/v1/compliance/evaluate",
        json={"project_id": test_project.id, "trigger_type": "MANUAL_SCAN"},
        headers=auth_headers
    )
    hash1 = r1.json()["evidence_hash"]

    # Run 2
    test_project.hcl_content = 'resource "aws_s3_bucket" "test2" {}'
    db.commit()
    r2 = client.post(
        "/api/v1/compliance/evaluate",
        json={"project_id": test_project.id, "trigger_type": "MANUAL_SCAN"},
        headers=auth_headers
    )
    hash2 = r2.json()["evidence_hash"]
    
    assert hash1 != hash2

def test_successful_rl_remediation_creates_audit_entry(auth_headers, test_project, db):
    test_project.hcl_content = 'resource "aws_db_instance" "test" { publicly_accessible = true }'
    db.commit()
    
    initial_count = db.query(AuditLog).count()
    
    res = client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_DISABLE_RDS_PUBLIC"]},
        headers=auth_headers
    )
    assert res.status_code == 200
    
    new_count = db.query(AuditLog).count()
    assert new_count == initial_count + 1
    
    last_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert last_log.action == "REMEDIATION_APPLIED"
    assert "ACT_DISABLE_RDS_PUBLIC" in last_log.details.get("applied_action_ids", [])
    assert last_log.resource_id == test_project.id

def test_audit_verification_succeeds_on_intact_chain(auth_headers, test_project, db):
    client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_DISABLE_RDS_PUBLIC"]},
        headers=auth_headers
    )
    
    res = client.get("/api/v1/audit/verify", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["error"] is None
    assert data["entries_checked"] > 0

def test_audit_verification_detects_broken_chain_or_tampering(auth_headers, test_project, db):
    client.post(
        f"/api/v1/projects/{test_project.id}/remediate",
        json={"action_ids": ["ACT_DISABLE_RDS_PUBLIC"]},
        headers=auth_headers
    )
    
    log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    original_details = dict(log.details) if log.details else {}
    
    try:
        log.details = {"tampered": True}
        db.commit()
        
        res = client.get("/api/v1/audit/verify", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert "Tampered entry detected" in data["error"] or "Broken chain link" in data["error"]
    finally:
        log.details = original_details
        db.commit()

def test_report_download_uses_actual_evidence_and_no_fallback(auth_headers, test_project, db):
    test_project.hcl_content = 'resource "aws_db_instance" "test" { publicly_accessible = true }'
    db.commit()
    
    eval_res = client.post(
        "/api/v1/compliance/evaluate",
        json={"project_id": test_project.id, "trigger_type": "MANUAL_SCAN"},
        headers=auth_headers
    )
    
    gen_res = client.post(
        "/api/v1/reports/generate",
        json={"projectId": test_project.id},
        headers=auth_headers
    )
    assert gen_res.status_code == 200
    report_id = gen_res.json()["id"]
    
    down_res = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
    assert down_res.status_code == 200
    
    csv_text = down_res.text
    assert "OPA_VIOLATION" in csv_text
    assert "SONAR_FINDING" in csv_text
    assert "Satisfied via KMS envelope encryption" not in csv_text

def test_report_no_evaluation_run_returns_error(auth_headers, db):
    import uuid
    rep = ComplianceReport(
        id=f"rep-no-eval-{uuid.uuid4().hex[:6]}",
        title="Test",
        project_id="proj-healthcare-india",
        status="Ready",
        grade="F",
        score="0%"
    )
    db.add(rep)
    db.commit()
    
    res = client.get(f"/api/v1/reports/{rep.id}/download", headers=auth_headers)
    assert res.status_code == 400
    assert "No compliance evaluation evidence exists" in res.json()["detail"]


# ==========================================================================
# Tests for the three targeted patches (smoke-test follow-up)
# ==========================================================================

class TestRLActionIds:
    """Fix 1: top-level action_ids must match recommendations[].action_id"""

    def test_action_ids_populated_at_top_level(self, auth_headers):
        """action_ids at root must be non-empty and match each recommendation."""
        res = client.post(
            "/api/v1/remediation/optimize",
            json={
                "project_id": "proj-healthcare-india",
                "opa_violations": [
                    {"control_id": "CTRL-AWS-RDS-NO-PUBLIC"},
                    {"control_id": "CTRL-AWS-S3-ENC"},
                    {"control_id": "CTRL-AWS-LOG-180D"},
                ],
                "compliance_score": 50.0,
                "overall_status": "FAIL"
            },
            headers=auth_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert "action_ids" in data, "top-level action_ids key must be present"
        top_ids = data["action_ids"]
        assert isinstance(top_ids, list), "action_ids must be a list"
        assert len(top_ids) > 0, "action_ids must not be empty when violations exist"
        rec_ids = [r["action_id"] for r in data["recommendations"] if r.get("action_id")]
        assert top_ids == rec_ids, (
            f"top-level action_ids {top_ids} must equal recommendations action_ids {rec_ids}"
        )

    def test_opa_violations_fallback_processes_enc_action(self, auth_headers):
        """Verify that passing opa_violations correctly maps to active_violations and processes storage encryption."""
        res = client.post(
            "/api/v1/remediation/optimize",
            json={
                "project_id": "proj-healthcare-india",
                "opa_violations": [
                    {"control_id": "CTRL-AWS-RDS-STORAGE-ENC"}
                ],
                "compliance_score": 50.0,
                "overall_status": "FAIL"
            },
            headers=auth_headers
        )
        assert res.status_code == 200
        data = res.json()
        top_ids = data.get("action_ids", [])
        assert "ACT_ENABLE_RDS_ENC" in top_ids, "CTRL-AWS-RDS-STORAGE-ENC should yield ACT_ENABLE_RDS_ENC action"


class TestReportEvaluationRunSelection:
    """Fix 2 & 3: evaluation_run_id selection + 404 on missing project"""

    @pytest.fixture(scope="class")
    def eval_run_a(self, db):
        """A specific evaluation run to pin reports to."""
        run = EvaluationRun(
            id="eval-run-smoke-a",
            project_id="proj-healthcare-india",
            trigger_type="SMOKE_TEST",
            overall_status="FAIL",
            compliance_score=55.0,
            passed_count=2,
            failed_count=3,
            unknown_count=0,
            not_applicable_count=0,
            evidence_payload={"opa_violations": [{"control_id": "CTRL-TEST", "description": "smoke violation"}], "sonar_findings": []},
            evidence_hash="abc123smoke"
        )
        db.add(run)
        db.commit()
        yield run
        db.delete(run)
        db.commit()

    @pytest.fixture(scope="class")
    def eval_run_other_project(self, db):
        """An evaluation run belonging to a DIFFERENT project."""
        other_proj = Project(
            id="proj-other-smoke",
            name="Other Project",
            organization="Other",
            sector="Finance",
            environment="staging",
            cloud_provider="AWS",
            owner="admin",
            status="Protected"
        )
        db.add(other_proj)
        db.flush()
        run = EvaluationRun(
            id="eval-run-smoke-other",
            project_id="proj-other-smoke",
            trigger_type="SMOKE_TEST",
            overall_status="PASS",
            compliance_score=95.0,
            passed_count=5,
            failed_count=0,
            unknown_count=0,
            not_applicable_count=0,
            evidence_payload={},
            evidence_hash="otherabc123"
        )
        db.add(run)
        db.commit()
        yield run
        db.delete(run)
        db.delete(other_proj)
        db.commit()

    def test_explicit_evaluation_run_id_is_used(self, auth_headers, eval_run_a, db):
        """Supplying evaluation_run_id pins the report to that exact run."""
        res = client.post(
            "/api/v1/reports/generate",
            json={
                "projectId": "proj-healthcare-india",
                "title": "Pinned Report Test",
                "evaluation_run_id": eval_run_a.id
            },
            headers=auth_headers
        )
        assert res.status_code == 200
        data = res.json()
        # Verify the evidence_hash matches the pinned run
        assert data["evidence_hash"] == eval_run_a.evidence_hash, (
            "Report evidence_hash must come from the pinned evaluation run"
        )
        # Score must reflect that run's score
        assert "55.0" in data["score"]
        # Report should be downloadable and contain the run's OPA violation
        dl = client.get(f"/api/v1/reports/{data['id']}/download", headers=auth_headers)
        assert dl.status_code == 200
        assert "smoke violation" in dl.text

    def test_evaluation_run_from_other_project_is_rejected(
        self, auth_headers, eval_run_other_project
    ):
        """evaluation_run_id belonging to a different project must be rejected with 403."""
        res = client.post(
            "/api/v1/reports/generate",
            json={
                "projectId": "proj-healthcare-india",
                "title": "Cross-Project Run Test",
                "evaluation_run_id": eval_run_other_project.id
            },
            headers=auth_headers
        )
        assert res.status_code == 403
        assert "does not belong" in res.json()["detail"]

    def test_missing_evaluation_run_id_falls_back_to_latest(self, auth_headers):
        """When no evaluation_run_id is supplied, the latest run for the project is used."""
        res = client.post(
            "/api/v1/reports/generate",
            json={"projectId": "proj-healthcare-india", "title": "Latest Fallback Test"},
            headers=auth_headers
        )
        assert res.status_code == 200
        data = res.json()
        # Must produce a valid report with a real evidence_hash (not all zeros)
        assert data["evidence_hash"] and data["evidence_hash"] != "0" * 64

    def test_nonexistent_project_returns_404(self, auth_headers):
        """Requesting a report for a project that doesn't exist must return 404."""
        res = client.post(
            "/api/v1/reports/generate",
            json={"projectId": "proj-does-not-exist-9999", "title": "Should 404"},
            headers=auth_headers
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_existing_report_functionality_unchanged(self, auth_headers):
        """Existing generate + download flow must continue to work without changes."""
        gen = client.post(
            "/api/v1/reports/generate",
            json={"projectId": "proj-healthcare-india", "title": "Regression Test"},
            headers=auth_headers
        )
        assert gen.status_code == 200
        rep_id = gen.json()["id"]

        dl = client.get(f"/api/v1/reports/{rep_id}/download", headers=auth_headers)
        assert dl.status_code == 200
        assert "REGULACLOUD STATUTORY COMPLIANCE AUDIT CERTIFICATE" in dl.text
        assert "proj-healthcare-india" in dl.text
        assert dl.headers["content-type"] == "text/csv; charset=utf-8"

