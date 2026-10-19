import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.auth import require_user

client = TestClient(app)

def override_require_user():
    return type('User', (), {'id': 1, 'role': 'ADMIN', 'email': 'admin@test.com'})()

def test_infrastructure_unauthenticated():
    response = client.get("/api/v1/projects/fake-id/infrastructure/topology")
    assert response.status_code == 401

def test_infrastructure_missing_project():
    app.dependency_overrides[require_user] = override_require_user
    try:
        response = client.get("/api/v1/projects/99999/infrastructure/topology")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(require_user, None)

def test_topology_a_to_i_full_lifecycle():
    from backend.app.core.database import SessionLocal
    from backend.app.db.models import Project, EvaluationRun
    from backend.app.core.hashing import compute_infrastructure_hash
    import uuid

    db = SessionLocal()
    pid = f"proj-topo-{uuid.uuid4().hex[:6]}"
    initial_hcl = 'resource "aws_s3_bucket" "test_bucket" {\n  bucket = "my-secure-bucket"\n}\n'
    initial_infra_hash = compute_infrastructure_hash(initial_hcl)

    project = Project(
        id=pid,
        name="Topology Test Project",
        organization="Ministry of Health",
        sector="Healthcare",
        owner="alice",
        hcl_content=initial_hcl
    )
    db.add(project)
    db.commit()

    def user_alice():
        return type('User', (), {'id': 'usr-alice', 'role': 'USER', 'username': 'alice', 'email': 'alice@test.gov.in'})()
    
    def user_bob():
        return type('User', (), {'id': 'usr-bob', 'role': 'USER', 'username': 'bob', 'email': 'bob@test.gov.in'})()

    def user_admin():
        return type('User', (), {'id': 'usr-admin', 'role': 'ADMIN', 'username': 'admin', 'email': 'admin@test.gov.in'})()

    try:
        # Test G: No evaluation -> defined NO_EVALUATION response
        app.dependency_overrides[require_user] = user_alice
        res_g = client.get(f"/api/v1/projects/{pid}/infrastructure/topology")
        assert res_g.status_code == 200
        assert res_g.json().get("status") == "NO_EVALUATION"

        # Create evaluation without native_plan_json (synthetic fallback)
        eval_run_synth = EvaluationRun(
            id=f"eval-synth-{uuid.uuid4().hex[:6]}",
            project_id=pid,
            trigger_type="MANUAL_SCAN",
            overall_status="PASS",
            compliance_score=100.0,
            evidence_hash="dummy-hash-1",
            evidence_payload={
                "infrastructure_hash": initial_infra_hash,
                "plan_hash": "synth-plan-hash-1"
            }
        )
        db.add(eval_run_synth)
        db.commit()

        # Test H: Evaluation without native_plan_json -> UNSUPPORTED_SOURCE
        res_h = client.get(f"/api/v1/projects/{pid}/infrastructure/topology")
        assert res_h.status_code == 200
        assert res_h.json().get("status") == "UNSUPPORTED_SOURCE"

        # Now create native plan evaluation
        native_plan_sample = {
            "planned_values": {
                "root_module": {
                    "resources": [
                        {
                            "address": "aws_s3_bucket.test_bucket",
                            "type": "aws_s3_bucket",
                            "name": "test_bucket",
                            "provider_name": "aws",
                            "values": {"bucket": "my-secure-bucket"}
                        }
                    ]
                }
            },
            "configuration": {
                "root_module": {
                    "resources": []
                }
            }
        }
        test_plan_hash = "plan-hash-native-999"
        eval_run_native = EvaluationRun(
            id=f"eval-native-{uuid.uuid4().hex[:6]}",
            project_id=pid,
            trigger_type="PRE_DEPLOY",
            overall_status="PASS",
            compliance_score=100.0,
            evidence_hash="native-evidence-hash-1",
            evidence_payload={
                "infrastructure_hash": initial_infra_hash,
                "plan_hash": test_plan_hash,
                "native_plan_json": native_plan_sample
            }
        )
        db.add(eval_run_native)
        db.commit()

        # Test A: evaluate native project -> GET topology -> 200, stale=false, nodes populated
        res_a = client.get(f"/api/v1/projects/{pid}/infrastructure/topology")
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["stale"] is False
        assert data_a["infrastructure_hash"] == initial_infra_hash
        assert len(data_a["resources"]) == 1
        assert data_a["resources"][0]["address"] == "aws_s3_bucket.test_bucket"

        # Test I: returned plan_hash == evidence_payload["plan_hash"]
        assert data_a["plan_hash"] == test_plan_hash

        # Test D: Owner USER -> 200
        app.dependency_overrides[require_user] = user_alice
        res_d = client.get(f"/api/v1/projects/{pid}/infrastructure/topology")
        assert res_d.status_code == 200

        # Test E: Different USER -> 403
        app.dependency_overrides[require_user] = user_bob
        res_e = client.get(f"/api/v1/projects/{pid}/infrastructure/topology")
        assert res_e.status_code == 403
        assert "Not authorized" in res_e.json()["detail"]

        # Test F: ADMIN -> 200
        app.dependency_overrides[require_user] = user_admin
        res_f = client.get(f"/api/v1/projects/{pid}/infrastructure/topology")
        assert res_f.status_code == 200

        # Test B: Modify HCL after evaluation -> stale=true
        app.dependency_overrides[require_user] = user_alice
        project.hcl_content = initial_hcl + '\nresource "aws_ebs_volume" "extra" { size = 20 }\n'
        db.commit()

        res_b = client.get(f"/api/v1/projects/{pid}/infrastructure/topology")
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["stale"] is True
        assert data_b["infrastructure_hash"] != initial_infra_hash

        # Test C: Re-evaluate -> stale=false
        new_infra_hash = compute_infrastructure_hash(project.hcl_content)
        eval_run_reeval = EvaluationRun(
            id=f"eval-native-{uuid.uuid4().hex[:6]}",
            project_id=pid,
            trigger_type="PRE_DEPLOY",
            overall_status="PASS",
            compliance_score=100.0,
            evidence_hash="native-evidence-hash-2",
            evidence_payload={
                "infrastructure_hash": new_infra_hash,
                "plan_hash": "new-plan-hash-111",
                "native_plan_json": native_plan_sample
            }
        )
        db.add(eval_run_reeval)
        db.commit()

        res_c = client.get(f"/api/v1/projects/{pid}/infrastructure/topology")
        assert res_c.status_code == 200
        data_c = res_c.json()
        assert data_c["stale"] is False
        assert data_c["infrastructure_hash"] == new_infra_hash
        assert data_c["plan_hash"] == "new-plan-hash-111"

    finally:
        app.dependency_overrides.pop(require_user, None)
        # Clean up database records
        db.query(EvaluationRun).filter(EvaluationRun.project_id == pid).delete()
        db.query(Project).filter(Project.id == pid).delete()
        db.commit()
        db.close()
