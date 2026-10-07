import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.auth import require_user

client = TestClient(app)

def override_require_user():
    return type('User', (), {'id': 1, 'role': 'ADMIN', 'email': 'admin@test.com'})()

def test_dashboard_stats_unauthenticated():
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 401

def test_dashboard_stats_authenticated():
    app.dependency_overrides[require_user] = override_require_user
    try:
        response = client.get("/api/v1/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "complianceScore" in data
        assert "securityFindings" in data
        assert "recentActivities" in data
        assert "trend" in data
    finally:
        app.dependency_overrides.pop(require_user, None)
