import pytest
import os
import tempfile
from backend.app.api.v1.remediation_rl import optimize_remediation
from backend.app.core.database import SessionLocal
from backend.app.db.init_db import init_database
from backend.app.engines.compliance_engine import ComplianceEngine
from backend.app.engines.sonarqube_client import SonarQubeClient
from backend.app.engines.rl_remediator import QLearningRemediationAgent
from backend.app.engines.terraform_engine import TerraformEngine

@pytest.fixture(scope="module")
def db():
    init_database()
    session = SessionLocal()
    yield session
    session.close()

def test_rl_remediation_endpoint_sequences_actions():
    """Verifies that the RL remediation endpoint returns optimal sequenced actions for all controls."""
    payload = {
        "active_violations": [
            "CTRL-AWS-RDS-NO-PUBLIC",
            "CTRL-AWS-S3-ENC",
            "CTRL-AWS-LOG-180D",
            "CTRL-SONAR-INJECTION-FREE",
            "CTRL-SONAR-ZERO-CRITICAL"
        ]
    }
    data = optimize_remediation(payload)
    assert data["model_type"] == "Tabular Q-Learning (Model-Free RL)"
    assert data["total_steps_required"] >= 3
    recs = data["recommendations"]
    action_ids = [r["action_id"] for r in recs]
    assert "ACT_ENABLE_S3_ENC" in action_ids or "ACT_DISABLE_RDS_PUBLIC" in action_ids
    assert "ACT_PATCH_SONAR_INJECTION" in action_ids or "ACT_UPGRADE_WEAK_CRYPTO" in action_ids

def test_sqli_scanner_catches_vulnerable_code_and_passes_remediated():
    """Verifies that static code analyzer catches raw SQL concatenation and passes parameterized PreparedStatement."""
    client = SonarQubeClient()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Vulnerable Controller
        vuln_file = os.path.join(tmp_dir, "PatientRecordController.java")
        with open(vuln_file, "w") as f:
            f.write("""
            package com.example;
            import java.sql.*;
            public class PatientRecordController {
                public void get(String id, Connection conn) throws Exception {
                    Statement stmt = conn.createStatement();
                    String query = "SELECT * FROM patients WHERE id = '" + id + "'";
                    stmt.executeQuery(query);
                }
            }
            """)
        
        findings_before = client.scan_source_directory(tmp_dir)
        assert len(findings_before) >= 1
        assert any(f["cwe"] == "CWE-89" for f in findings_before)
        
        # 2. Remediated Controller
        with open(vuln_file, "w") as f:
            f.write("""
            package com.example;
            import java.sql.*;
            public class PatientRecordController {
                public void get(String id, Connection conn) throws Exception {
                    String query = "SELECT * FROM patients WHERE id = ?";
                    PreparedStatement ps = conn.prepareStatement(query);
                    ps.setString(1, id);
                    ps.executeQuery();
                }
            }
            """)
        
        findings_after = client.scan_source_directory(tmp_dir)
        assert len(findings_after) == 0

def test_crypto_scanner_catches_des_and_passes_aes_gcm():
    """Verifies that static code analyzer catches insecure DES cipher and passes AES authenticated cipher."""
    client = SonarQubeClient()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Insecure DES file
        crypto_file = os.path.join(tmp_dir, "EncryptionService.java")
        with open(crypto_file, "w") as f:
            f.write("""
            package com.example;
            import javax.crypto.Cipher;
            import javax.crypto.spec.SecretKeySpec;
            public class EncryptionService {
                public void enc(byte[] k) throws Exception {
                    SecretKeySpec key = new SecretKeySpec(k, "DES");
                    Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
                }
            }
            """)
        
        findings_before = client.scan_source_directory(tmp_dir)
        assert len(findings_before) >= 1
        assert any(f["cwe"] == "CWE-327" for f in findings_before)
        
        # 2. Secure AES-GCM file
        with open(crypto_file, "w") as f:
            f.write("""
            package com.example;
            import javax.crypto.Cipher;
            import javax.crypto.spec.SecretKeySpec;
            public class EncryptionService {
                public void enc(byte[] k) throws Exception {
                    SecretKeySpec key = new SecretKeySpec(k, "AES");
                    Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
                }
            }
            """)
        
        findings_after = client.scan_source_directory(tmp_dir)
        assert len(findings_after) == 0

def test_sonarqube_unavailable_returns_unknown_and_blocks_deployment(db):
    """Verifies that if SonarQube verification is unavailable, requirement state is UNKNOWN and deployment is strictly blocked."""
    good_hcl = TerraformEngine.generate_compliant_hcl({
        "aws_region": "ap-south-1",
        "environment": "production"
    })
    
    result = ComplianceEngine.evaluate_compliance(
        db=db,
        project_id="proj-ayushman-portal",
        hcl_code=good_hcl,
        sonar_project_key="unavailable"
    )
    
    assert result["overall_status"] == "FAIL"
    assert result["deployment_allowed"] is False
    assert result["unknown_count"] >= 1
    # Find mandatory Sonar requirement
    sonar_req = next((r for r in result["evaluations"] if r["requirement_id"] == "DPDPR-2025-R8.3"), None)
    assert sonar_req is not None
    assert sonar_req["status"] == "UNKNOWN"

def test_remediation_transition_fail_to_pass(db):
    """Verifies that full remediation across HCL and code produces a deterministic PASS with deployment unblocked."""
    # 1. Non-compliant HCL (vulnerable DB and retention)
    bad_hcl = """
    resource "aws_db_instance" "bad_db" {
      publicly_accessible = true
      storage_encrypted = false
    }
    """
    eval_bad = ComplianceEngine.evaluate_compliance(
        db=db,
        project_id="proj-ayushman-portal",
        hcl_code=bad_hcl
    )
    assert eval_bad["overall_status"] == "FAIL"
    assert eval_bad["deployment_allowed"] is False
    
    # 2. Compliant Remediated HCL
    good_hcl = TerraformEngine.generate_compliant_hcl({
        "aws_region": "ap-south-1",
        "environment": "production"
    })
    eval_good = ComplianceEngine.evaluate_compliance(
        db=db,
        project_id="proj-ayushman-portal",
        hcl_code=good_hcl
    )
    assert eval_good["overall_status"] == "PASS"
    assert eval_good["deployment_allowed"] is True
    assert eval_good["compliance_score"] == 100.0
    assert eval_good["failed_count"] == 0
    assert len(eval_good["evidence_hash"]) == 64

def test_rl_optimizer_cannot_modify_deployment_authority():
    """Verifies that the RL engine is strictly a recommendation tool and lacks authority to alter evaluation runs or deployment state."""
    agent = QLearningRemediationAgent()
    recs = agent.recommend_remediations(["CTRL-AWS-RDS-NO-PUBLIC"])
    assert isinstance(recs, list)
    # The agent does not have database sessions, commit methods, or approval tokens
    assert not hasattr(agent, "approve_deployment")
    assert not hasattr(agent, "set_compliance_state")
