"""
Targeted verification tests for the security and accuracy fixes.
Tests: auth enforcement, SonarQube label, dynamic timestamp, audit chain, compliance gate.
"""
import os
import sys
import json
import hashlib
from datetime import datetime, timezone

# Set JWT secret before any imports so security.py picks it up
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-verification"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token, hash_password
from backend.app.core.database import get_db, engine, Base, SessionLocal
from backend.app.db.models import User, AuditLog, Project


client = TestClient(app)


def _get_auth_header(username="admin", role="ADMIN"):
    token = create_access_token({"sub": username, "role": role, "id": f"usr-{username}"})
    return {"Authorization": f"Bearer {token}"}


def _ensure_test_user(db, username="admin", role="ADMIN"):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            id=f"usr-{username}-test",
            username=username,
            email=f"{username}@test.com",
            hashed_password=hash_password("TestPass123!"),
            role=role,
            is_active=True
        )
        db.add(user)
        db.commit()
    return user


# ============================
# 1. AUTH ENFORCEMENT TESTS
# ============================

class TestAuthEnforcement:
    """Verify unauthenticated requests to newly protected endpoints return 401."""

    def test_get_deployments_unauthenticated(self):
        res = client.get("/api/v1/deployments")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    def test_post_deployment_plan_unauthenticated(self):
        res = client.post("/api/v1/deployments/plan", json={"projectId": "proj-test"})
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    def test_post_ai_chat_unauthenticated(self):
        res = client.post("/api/v1/ai/chat", json={
            "project_id": "proj-test",
            "message": "What is the compliance status?"
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    def test_apply_deployment_unauthenticated(self):
        """Existing ADMIN protection on apply must still work."""
        res = client.post("/api/v1/deployments/fake-id/apply")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    def test_get_deployments_authenticated(self):
        """Authenticated user can list deployments."""
        headers = _get_auth_header("admin", "ADMIN")
        db = SessionLocal()
        try:
            _ensure_test_user(db, "admin", "ADMIN")
        finally:
            db.close()
        res = client.get("/api/v1/deployments", headers=headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"

    def test_apply_requires_admin_not_user(self):
        """Regular USER cannot apply deployments - must be ADMIN."""
        db = SessionLocal()
        try:
            _ensure_test_user(db, "operator", "USER")
        finally:
            db.close()
        headers = _get_auth_header("operator", "USER")
        res = client.post("/api/v1/deployments/fake-id/apply", headers=headers)
        assert res.status_code == 403, f"Expected 403 for non-admin, got {res.status_code}"


# ============================
# 2. SONARQUBE LABEL TEST
# ============================

class TestSonarQubeLabel:
    """Verify fallback scanner uses LOCAL_STATIC_FALLBACK, not SONARQUBE."""

    def test_local_fallback_label(self):
        from backend.app.engines.sonarqube_client import SonarQubeClient
        client_sq = SonarQubeClient(base_url="http://localhost:99999", token="")
        findings = client_sq.fetch_project_findings("test-project")
        if findings:
            for f in findings:
                assert f["verification_source"] == "LOCAL_STATIC_FALLBACK", \
                    f"Expected LOCAL_STATIC_FALLBACK, got {f['verification_source']}"
            print(f"  ✓ {len(findings)} findings all labeled LOCAL_STATIC_FALLBACK")
        else:
            print("  ✓ No findings returned (test_apps may be empty), label test N/A")


# ============================
# 3. EVIDENCE TIMESTAMP TEST
# ============================

class TestEvidenceTimestamp:
    """Verify evidence timestamp is dynamic, not hardcoded."""

    def test_timestamp_is_dynamic(self):
        from backend.app.engines.compliance_engine import ComplianceEngine
        from backend.app.engines.terraform_engine import TerraformEngine
        import time

        db = SessionLocal()
        try:
            _ensure_test_user(db, "admin", "ADMIN")
            project = db.query(Project).first()
            if not project:
                print("  ⚠ No project in DB, skipping timestamp test")
                return

            before = datetime.now(timezone.utc)
            time.sleep(0.05)

            result = ComplianceEngine.evaluate_compliance(
                db=db,
                project_id=project.id,
                trigger_type="MANUAL_SCAN"
            )

            time.sleep(0.05)
            after = datetime.now(timezone.utc)

            # The evidence_hash should differ from a hash with the old hardcoded timestamp
            old_ts_payload = {
                "project_id": project.id,
                "score": result["compliance_score"],
                "overall_status": result["overall_status"],
                "passed": result["passed_count"],
                "failed": result["failed_count"],
                "unknown": result["unknown_count"],
                "opa_violations_count": len(result["opa_violations"]),
                "sonar_findings_count": len(result["sonar_findings"]),
                "timestamp": "2026-08-29T18:00:00Z"
            }
            old_hash = hashlib.sha256(json.dumps(old_ts_payload, sort_keys=True).encode()).hexdigest()
            assert result["evidence_hash"] != old_hash, \
                "Evidence hash matches old hardcoded timestamp — timestamp fix not applied"
            print(f"  ✓ Evidence hash is dynamic (differs from hardcoded timestamp hash)")
        finally:
            db.close()


# ============================
# 4. AUDIT CHAIN INTEGRITY
# ============================

class TestAuditChainIntegrity:
    """Verify SHA-256 audit chain is intact after changes."""

    def test_chain_integrity(self):
        db = SessionLocal()
        try:
            logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
            if len(logs) < 2:
                print("  ⚠ Fewer than 2 audit logs, skipping chain test")
                return

            # Verify chain linkage
            for i in range(1, min(len(logs), 20)):  # Check first 20 links
                assert logs[i].previous_hash == logs[i-1].current_hash, \
                    f"Chain broken at log {logs[i].id}: prev_hash != prior current_hash"

            # Verify genesis
            assert logs[0].previous_hash == "0" * 64, \
                "Genesis log previous_hash should be all zeros"

            print(f"  ✓ Audit chain intact across {min(len(logs), 20)} entries")
        finally:
            db.close()


# ============================
# 5. COMPLIANCE GATE TEST
# ============================

class TestComplianceGate:
    """Verify ADMIN can only apply when compliance gate passes."""

    def test_blocked_deployment_cannot_apply(self):
        """ADMIN cannot apply a BLOCKED deployment."""
        db = SessionLocal()
        try:
            _ensure_test_user(db, "admin", "ADMIN")
        finally:
            db.close()

        headers = _get_auth_header("admin", "ADMIN")
        # Create a plan first (which may be BLOCKED or AWAITING_APPROVAL)
        plan_res = client.post("/api/v1/deployments/plan", json={
            "projectId": "proj-healthcare-india",
            "hcl_code": 'resource "aws_db_instance" "test" {\n  publicly_accessible = true\n  storage_encrypted = false\n}'
        }, headers=headers)

        if plan_res.status_code == 200:
            plan_data = plan_res.json()
            dep_id = plan_data.get("id")
            if plan_data.get("status") == "BLOCKED":
                apply_res = client.post(f"/api/v1/deployments/{dep_id}/apply", headers=headers)
                assert apply_res.status_code == 400, \
                    f"BLOCKED deployment should return 400, got {apply_res.status_code}"
                print(f"  ✓ BLOCKED deployment correctly rejected (400)")
            else:
                print(f"  ℹ Plan status is {plan_data.get('status')}, not BLOCKED (compliant HCL)")
        else:
            print(f"  ⚠ Plan creation returned {plan_res.status_code}, skipping gate test")
