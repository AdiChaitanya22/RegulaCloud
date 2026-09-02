import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.db.init_db import init_database
from backend.app.db.models import Project, User, Deployment, EvaluationRun, ComplianceReport, SystemSetting
from backend.app.core.security import hash_password, create_access_token
from backend.app.engines.compliance_engine import ComplianceEngine

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_database()

@pytest.fixture
def client():
    return TestClient(app)

def test_project_edit_put_endpoint(client):
    # Test editing an existing project
    res = client.put("/api/v1/projects/proj-healthcare-india", json={
        "name": "Ayushman Digital Health Registry (Updated)",
        "owner": "new.director@mohfw.gov.in"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Ayushman Digital Health Registry (Updated)"
    assert data["owner"] == "new.director@mohfw.gov.in"

    # Test 404 for non-existent project
    res_404 = client.put("/api/v1/projects/non-existent-proj", json={"name": "Test"})
    assert res_404.status_code == 404

def test_auth_and_rbac_flow(client):
    # 1. Successful Admin Login
    login_res = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "AdminPassword123!"
    })
    assert login_res.status_code == 200
    admin_token = login_res.json()["access_token"]
    assert login_res.json()["role"] == "ADMIN"

    # 2. Successful User Login
    user_login = client.post("/api/v1/auth/login", json={
        "username": "operator",
        "password": "UserPassword123!"
    })
    assert user_login.status_code == 200
    user_token = user_login.json()["access_token"]
    assert user_login.json()["role"] == "USER"

    # 3. Invalid credentials
    invalid_login = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "WrongPassword!"
    })
    assert invalid_login.status_code == 401

    # 4. Profile endpoint
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin"
    assert me_res.json()["role"] == "ADMIN"

def test_deployment_apply_authorization_and_gate_protection(client):
    # Obtain admin and user tokens
    admin_token = create_access_token({"sub": "admin", "role": "ADMIN", "id": "usr-admin-01"})
    user_token = create_access_token({"sub": "operator", "role": "USER", "id": "usr-operator-02"})

    db = SessionLocal()
    try:
        # Create a blocked deployment
        blocked_dep = Deployment(
            id="dep-test-blocked",
            project_id="proj-healthcare-india",
            status="BLOCKED",
            logs=["[ERROR] Mandatory controls violated."]
        )
        db.merge(blocked_dep)
        db.commit()
    finally:
        db.close()

    # 1. Unauthenticated apply attempt -> 401
    res_unauth = client.post("/api/v1/deployments/dep-test-blocked/apply")
    assert res_unauth.status_code == 401

    # 2. Standard user (non-admin) apply attempt -> 403 Forbidden
    res_user = client.post(
        "/api/v1/deployments/dep-test-blocked/apply",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res_user.status_code == 403
    assert "Administrator authorization required" in res_user.json()["detail"]

    # 3. Admin apply attempt on BLOCKED deployment -> 400 Bad Request
    res_admin_blocked = client.post(
        "/api/v1/deployments/dep-test-blocked/apply",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin_blocked.status_code == 400
    assert "Cannot apply a BLOCKED deployment" in res_admin_blocked.json()["detail"]

def test_dynamic_compliance_summary(client):
    res = client.get("/api/v1/compliance/summary")
    assert res.status_code == 200
    data = res.json()
    assert "overallScore" in data
    assert "frameworks" in data
    assert len(data["frameworks"]) >= 2
    assert "passed" in data
    assert "failed" in data

def test_dynamic_policies_status(client):
    res = client.get("/api/v1/policies")
    assert res.status_code == 200
    policies = res.json()
    assert len(policies) > 0
    for p in policies:
        assert p["status"] in ["PASS", "FAIL", "UNKNOWN"]
        assert "framework" in p

def test_dynamic_dashboard_stats(client):
    res = client.get("/api/v1/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert "complianceScore" in data
    assert "monitoredControls" in data
    assert "activeProjects" in data
    assert "recentActivities" in data
    assert isinstance(data["recentActivities"], list)

def test_reports_generate_and_download_flow(client):
    # 1. List reports
    list_res = client.get("/api/v1/reports")
    assert list_res.status_code == 200
    reports = list_res.json()
    assert len(reports) >= 2

    # 2. Generate report
    gen_res = client.post("/api/v1/reports/generate", json={
        "title": "Automated Government Health Registry Audit",
        "projectId": "proj-healthcare-india"
    })
    assert gen_res.status_code == 200
    new_report = gen_res.json()
    rep_id = new_report["id"]
    assert rep_id.startswith("rep-")

    # 3. Download CSV report
    dl_res = client.get(f"/api/v1/reports/{rep_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "text/csv; charset=utf-8"
    assert "REGULACLOUD STATUTORY COMPLIANCE AUDIT CERTIFICATE" in dl_res.text
    assert rep_id in dl_res.text

def test_settings_persistence(client):
    # 1. Get settings
    get_res = client.get("/api/v1/settings")
    assert get_res.status_code == 200

    # 2. Save settings
    save_res = client.post("/api/v1/settings", json={
        "awsArn": "arn:aws:iam::999988887777:role/RegulaCloudCustomRole",
        "azureTenant": "4fa38c92-38ef-4122-8321-75bf22e391aa",
        "slackWebhook": "https://hooks.slack.com/services/T00/B00/X00",
        "rulesPci": True,
        "rulesSoc": True,
        "rulesHipaa": True,
        "scanIntervalHours": 2,
        "enforcementMode": "FailClosed"
    })
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "SUCCESS"

    # 3. Verify persistence
    verify_res = client.get("/api/v1/settings")
    assert verify_res.status_code == 200
    assert verify_res.json()["awsArn"] == "arn:aws:iam::999988887777:role/RegulaCloudCustomRole"
    assert verify_res.json()["rulesHipaa"] is True
