import os
import shutil
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.engines.application_remediator import ApplicationRemediator
from backend.app.engines.terraform_engine import TerraformEngine
from backend.app.engines.sonarqube_client import SonarQubeClient
from backend.app.db.models import Project

# Helper function to create dummy vulnerable java files
def create_vulnerable_java_files(temp_dir: str):
    os.makedirs(temp_dir, exist_ok=True)
    
    # Vulnerable Crypto File
    crypto_content = """
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class EncryptionService {
    public void encrypt(byte[] keyBytes, byte[] data) throws Exception {
        SecretKeySpec key = new SecretKeySpec(keyBytes, "DES");
        Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
    }
}
"""
    with open(os.path.join(temp_dir, "EncryptionService.java"), "w", encoding="utf-8") as f:
        f.write(crypto_content)
        
    # Vulnerable SQLi File
    sqli_content = """
import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;

public class PatientRecordController {
    public void getUser(Connection conn, String userId) throws Exception {
        String query = "SELECT * FROM users WHERE id = " + userId;
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(query);
    }
}
"""
    with open(os.path.join(temp_dir, "PatientRecordController.java"), "w", encoding="utf-8") as f:
        f.write(sqli_content)


def test_des_3des_source_remediation_and_idempotency(tmpdir):
    source_path = str(tmpdir.mkdir("src"))
    create_vulnerable_java_files(source_path)
    
    # 1. Apply remediation
    applied, skipped, changed = ApplicationRemediator.apply_source_actions(
        source_path, ["ACT_UPGRADE_WEAK_CRYPTO"]
    )
    
    assert "ACT_UPGRADE_WEAK_CRYPTO" in applied
    assert len(changed) == 1
    assert "EncryptionService.java" in changed[0]
    
    with open(changed[0], "r") as f:
        content = f.read()
        assert 'new SecretKeySpec(keyBytes, "AES")' in content
        assert 'Cipher.getInstance("AES/GCM/NoPadding")' in content
        assert "DES" not in content
        
    # 2. Test Idempotency
    applied2, skipped2, changed2 = ApplicationRemediator.apply_source_actions(
        source_path, ["ACT_UPGRADE_WEAK_CRYPTO"]
    )
    assert len(applied2) == 0
    assert len(changed2) == 0
    assert any("No vulnerable" in s for s in skipped2)


def test_sql_injection_source_remediation_and_idempotency(tmpdir):
    source_path = str(tmpdir.mkdir("src2"))
    create_vulnerable_java_files(source_path)
    
    applied, skipped, changed = ApplicationRemediator.apply_source_actions(
        source_path, ["ACT_PARAMETERIZE_SQL_QUERIES"]
    )
    
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in applied
    assert len(changed) == 1
    assert "PatientRecordController.java" in changed[0]
    
    with open(changed[0], "r") as f:
        content = f.read()
        assert 'PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");' in content
        assert 'ps.setString(1, userId);' in content
        assert 'ResultSet rs = ps.executeQuery();' in content
        assert 'executeQuery(query)' not in content
        
    # Test Idempotency
    applied2, skipped2, changed2 = ApplicationRemediator.apply_source_actions(
        source_path, ["ACT_PARAMETERIZE_SQL_QUERIES"]
    )
    assert len(applied2) == 0
    assert len(changed2) == 0


def test_cloudtrail_terraform_remediation_and_idempotency():
    base_hcl = 'resource "aws_cloudtrail" "trail" {\n  name = "audit"\n}'
    
    new_hcl, applied, skipped = TerraformEngine.apply_rl_actions(base_hcl, ["ACT_ENABLE_CLOUDTRAIL_MULTI"])
    
    assert "ACT_ENABLE_CLOUDTRAIL_MULTI" in applied
    assert 'is_multi_region_trail = true' in new_hcl
    assert 'enable_logging = true' in new_hcl
    
    # Idempotency
    new_hcl2, applied2, skipped2 = TerraformEngine.apply_rl_actions(new_hcl, ["ACT_ENABLE_CLOUDTRAIL_MULTI"])
    # Note: Terraform engine regex logic in apply_rl_actions appends if not present or replaces if present.
    # It still technically "applies" the action by replacing true with true.
    assert 'is_multi_region_trail = true' in new_hcl2
    # Ensure it doesn't duplicate
    assert new_hcl2.count('is_multi_region_trail = true') == 1


def test_re_scan_after_source_remediation(tmpdir):
    source_path = str(tmpdir.mkdir("src_scan"))
    create_vulnerable_java_files(source_path)
    
    client = SonarQubeClient(base_url="http://mock", token="mock")
    
    # 1. Scan before remediation
    findings_before = client.scan_source_directory(source_path)
    assert any(f["cwe"] == "CWE-89" for f in findings_before)
    assert any(f["cwe"] == "CWE-327" for f in findings_before)
    
    # 2. Remediate both
    ApplicationRemediator.apply_source_actions(source_path, ["ACT_PARAMETERIZE_SQL_QUERIES", "ACT_UPGRADE_WEAK_CRYPTO"])
    
    # 3. Scan after remediation
    findings_after = client.scan_source_directory(source_path)
    assert not any(f["cwe"] == "CWE-89" for f in findings_after)
    assert not any(f["cwe"] == "CWE-327" for f in findings_after)


def test_project_isolation(tmpdir):
    source_path_proj_A = str(tmpdir.mkdir("projA"))
    source_path_proj_B = str(tmpdir.mkdir("projB"))
    
    create_vulnerable_java_files(source_path_proj_A)
    create_vulnerable_java_files(source_path_proj_B)
    
    # Apply to A only
    ApplicationRemediator.apply_source_actions(source_path_proj_A, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    
    # Verify B is untouched
    with open(os.path.join(source_path_proj_B, "PatientRecordController.java"), "r") as f:
        content = f.read()
        assert "PreparedStatement" not in content
        assert "executeQuery(query)" in content
