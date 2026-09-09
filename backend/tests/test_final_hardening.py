import os
import sys

# Ensure test environment explicitly supplies a test secret
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-verification"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.db.models import Deployment
import importlib
import pytest

client = TestClient(app)

def test_unauthenticated_read_only_apis_rejected():
    endpoints = [
        "/api/v1/projects",
        "/api/v1/audit/logs",
        "/api/v1/settings",
        "/api/v1/dashboard/stats",
        "/api/v1/policies"
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"

def test_missing_jwt_secret_fails_in_production():
    # Save the original env vars
    original_secret = os.environ.get("JWT_SECRET_KEY")
    
    try:
        # Delete the secret
        if "JWT_SECRET_KEY" in os.environ:
            del os.environ["JWT_SECRET_KEY"]
            
        import backend.app.core.security
        
        # Reloading should raise ValueError
        with pytest.raises(ValueError) as exc:
            importlib.reload(backend.app.core.security)
            
        assert "JWT_SECRET_KEY environment variable is missing" in str(exc.value)
        assert "MUST be set in all environments" in str(exc.value)
    finally:
        # Restore
        if original_secret is not None:
            os.environ["JWT_SECRET_KEY"] = original_secret
        importlib.reload(backend.app.core.security)

def test_empty_deployment_db_returns_empty_list():
    from backend.app.core.security import create_access_token
    token = create_access_token({"sub": "admin", "role": "ADMIN", "id": "usr-admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    db = SessionLocal()
    try:
        # Save original deployments
        original_deployments = db.query(Deployment).all()
        for d in original_deployments:
            db.delete(d)
        db.commit()
        
        response = client.get("/api/v1/deployments", headers=headers)
        assert response.status_code == 200
        assert response.json() == []  # MUST be empty list, no mock fallback!
        
        # Restore
        from sqlalchemy.orm import make_transient
        for d in original_deployments:
            make_transient(d)
            db.add(d)
        db.commit()
    finally:
        db.close()
