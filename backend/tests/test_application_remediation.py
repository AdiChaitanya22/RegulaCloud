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


def test_java_sql_remediation_a_to_i(tmpdir):
    import subprocess
    from backend.app.engines.sonarqube_client import SonarQubeClient

    client = SonarQubeClient(base_url="http://mock", token="mock")

    # Test A: standard Connection conn pattern
    src_a = str(tmpdir.mkdir("src_a"))
    file_a = os.path.join(src_a, "StandardService.java")
    with open(file_a, "w") as f:
        f.write('''
import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;

public class StandardService {
    public void getUser(Connection conn, String id) throws Exception {
        String query = "SELECT * FROM users WHERE id = " + id;
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(query);
    }
}
''')
    app_a, skp_a, chg_a = ApplicationRemediator.apply_source_actions(src_a, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_a
    with open(file_a) as f:
        content_a = f.read()
    assert 'PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");' in content_a
    assert 'ps.setString(1, id);' in content_a
    assert 'ResultSet rs = ps.executeQuery();' in content_a

    # Test B: alternative connection variable name (e.g. dbConnection)
    src_b = str(tmpdir.mkdir("src_b"))
    file_b = os.path.join(src_b, "CustomConnService.java")
    with open(file_b, "w") as f:
        f.write('''
import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;

public class CustomConnService {
    public void getRecord(Connection dbConnection, String recId) throws Exception {
        String sql = "SELECT * FROM records WHERE id = " + recId;
        Statement statement = dbConnection.createStatement();
        ResultSet rs = statement.executeQuery(sql);
    }
}
''')
    app_b, skp_b, chg_b = ApplicationRemediator.apply_source_actions(src_b, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_b
    with open(file_b) as f:
        content_b = f.read()
    assert 'PreparedStatement ps = dbConnection.prepareStatement("SELECT * FROM records WHERE id = ?");' in content_b
    assert 'ps.setString(1, recId);' in content_b

    # Test C: executeQuery updated correctly and old query variable reference replaced
    assert 'executeQuery(sql)' not in content_b
    assert 'ResultSet rs = ps.executeQuery();' in content_b

    # Test D: supported execute(...) pattern handled correctly
    src_d = str(tmpdir.mkdir("src_d"))
    file_d = os.path.join(src_d, "ExecuteService.java")
    with open(file_d, "w") as f:
        f.write('''
import java.sql.Connection;
import java.sql.Statement;

public class ExecuteService {
    public void deleteRecord(Connection conn, String recId) throws Exception {
        String q = "SELECT * FROM records WHERE id = " + recId;
        Statement stmt = conn.createStatement();
        stmt.execute(q);
    }
}
''')
    app_d, _, _ = ApplicationRemediator.apply_source_actions(src_d, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_d
    with open(file_d) as f:
        content_d = f.read()
    assert 'ps.execute();' in content_d
    assert 'execute(q)' not in content_d

    # Test E: already parameterized code unchanged (idempotency)
    app_e, skp_e, chg_e = ApplicationRemediator.apply_source_actions(src_a, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert len(app_e) == 0
    assert len(chg_e) == 0
    with open(file_a) as f:
        assert f.read() == content_a

    # Test F: comment false positive unchanged
    src_f = str(tmpdir.mkdir("src_f"))
    file_f = os.path.join(src_f, "CommentService.java")
    comment_code = '''
public class CommentService {
    // String query = "SELECT * FROM users WHERE id = " + userId;
    /* String sql = "SELECT * FROM records WHERE id = " + recId; */
}
'''
    with open(file_f, "w") as f:
        f.write(comment_code)
    app_f, skp_f, chg_f = ApplicationRemediator.apply_source_actions(src_f, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert len(app_f) == 0
    with open(file_f) as f:
        assert f.read() == comment_code

    # Test G: complex concatenation (> 2 '+') safe skipped
    src_g = str(tmpdir.mkdir("src_g"))
    file_g = os.path.join(src_g, "ComplexService.java")
    complex_code = '''
import java.sql.Connection;
import java.sql.Statement;

public class ComplexService {
    public void search(Connection conn, String a, String b, String c) throws Exception {
        String query = "SELECT * FROM users WHERE id = " + a + " AND name = " + b + " AND role = " + c;
        Statement stmt = conn.createStatement();
        stmt.executeQuery(query);
    }
}
'''
    with open(file_g, "w") as f:
        f.write(complex_code)
    app_g, skp_g, chg_g = ApplicationRemediator.apply_source_actions(src_g, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert len(app_g) == 0
    with open(file_g) as f:
        assert f.read() == complex_code

    # Test H: unrelated code preserved byte-for-byte
    src_h = str(tmpdir.mkdir("src_h"))
    file_h = os.path.join(src_h, "MixedService.java")
    mixed_code = '''
import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;

public class MixedService {
    public int calculateScore(int a, int b) {
        return a * 10 + b;
    }

    public void runQuery(Connection conn, String id) throws Exception {
        String query = "SELECT * FROM logs WHERE id = " + id;
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(query);
    }
}
'''
    with open(file_h, "w") as f:
        f.write(mixed_code)
    app_h, _, _ = ApplicationRemediator.apply_source_actions(src_h, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_h
    with open(file_h) as f:
        content_h = f.read()
    assert "public int calculateScore(int a, int b) {\n        return a * 10 + b;\n    }" in content_h

    # Test I: self-contained javac integration test
    src_i = str(tmpdir.mkdir("src_i"))
    pkg_dir = os.path.join(src_i, "com", "regulacloud", "test")
    os.makedirs(pkg_dir, exist_ok=True)
    java_file_i = os.path.join(pkg_dir, "CompilableService.java")
    # Pre-remediation source intentionally does NOT import PreparedStatement
    compilable_code = '''package com.regulacloud.test;

import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;

public class CompilableService {
    public void executeSearch(Connection conn, String queryParam) throws Exception {
        String query = "SELECT * FROM patients WHERE id = " + queryParam;
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(query);
    }
}
'''
    with open(java_file_i, "w") as f:
        f.write(compilable_code)

    # Compile before remediation
    out_dir_before = str(tmpdir.mkdir("out_before"))
    res_compile_before = subprocess.run(["javac", "-d", out_dir_before, java_file_i], capture_output=True, text=True)
    assert res_compile_before.returncode == 0, f"Compilation failed before: {res_compile_before.stderr}"

    # Verify scanner detects CWE-89 before remediation
    findings_before = client.scan_source_directory(src_i)
    assert any(f["cwe"] == "CWE-89" for f in findings_before)

    # Apply remediation
    app_i, _, chg_i = ApplicationRemediator.apply_source_actions(src_i, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_i
    assert len(chg_i) == 1

    with open(java_file_i) as f:
        content_after = f.read()

    # PreparedStatement import gained automatically
    assert "import java.sql.PreparedStatement;" in content_after
    assert 'PreparedStatement ps = conn.prepareStatement("SELECT * FROM patients WHERE id = ?");' in content_after

    # Compile after remediation with javac
    out_dir_after = str(tmpdir.mkdir("out_after"))
    res_compile_after = subprocess.run(["javac", "-d", out_dir_after, java_file_i], capture_output=True, text=True)
    assert res_compile_after.returncode == 0, f"Compilation failed after remediation: {res_compile_after.stderr}"

    # Verify scanner confirms CWE-89 absent after remediation
    findings_after = client.scan_source_directory(src_i)
    assert not any(f["cwe"] == "CWE-89" for f in findings_after)

    # Idempotency check: second remediation leaves file unchanged
    app_i2, skp_i2, chg_i2 = ApplicationRemediator.apply_source_actions(src_i, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert len(chg_i2) == 0
    with open(java_file_i) as f:
        content_after_2 = f.read()
    assert content_after_2 == content_after


def test_prepared_statement_import_cases_a_to_f(tmpdir):
    from backend.app.engines.application_remediator import ApplicationRemediator

    # CASE A: missing PreparedStatement import -> remediation adds exactly one
    src_a = str(tmpdir.mkdir("import_case_a"))
    file_a = os.path.join(src_a, "CaseA.java")
    with open(file_a, "w") as f:
        f.write('''package com.example;

import java.sql.Connection;
import java.sql.Statement;
import java.sql.ResultSet;

public class CaseA {
    public void query(Connection conn, String id) throws Exception {
        String sql = "SELECT * FROM t WHERE id = " + id;
        Statement s = conn.createStatement();
        ResultSet rs = s.executeQuery(sql);
    }
}
''')
    app_a, _, chg_a = ApplicationRemediator.apply_source_actions(src_a, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_a
    with open(file_a) as f:
        content_a = f.read()
    assert content_a.count("import java.sql.PreparedStatement;") == 1
    # Check placement: immediately after java.sql.ResultSet
    lines_a = content_a.splitlines()
    rs_idx = next(i for i, l in enumerate(lines_a) if "import java.sql.ResultSet;" in l)
    assert "import java.sql.PreparedStatement;" in lines_a[rs_idx + 1]

    # CASE B: explicit PreparedStatement import already exists -> no duplicate
    src_b = str(tmpdir.mkdir("import_case_b"))
    file_b = os.path.join(src_b, "CaseB.java")
    with open(file_b, "w") as f:
        f.write('''package com.example;

import java.sql.Connection;
import java.sql.Statement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

public class CaseB {
    public void query(Connection conn, String id) throws Exception {
        String sql = "SELECT * FROM t WHERE id = " + id;
        Statement s = conn.createStatement();
        ResultSet rs = s.executeQuery(sql);
    }
}
''')
    app_b, _, chg_b = ApplicationRemediator.apply_source_actions(src_b, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_b
    with open(file_b) as f:
        content_b = f.read()
    assert content_b.count("import java.sql.PreparedStatement;") == 1

    # CASE C: java.sql.* exists -> no explicit PreparedStatement import added
    src_c = str(tmpdir.mkdir("import_case_c"))
    file_c = os.path.join(src_c, "CaseC.java")
    with open(file_c, "w") as f:
        f.write('''package com.example;

import java.sql.*;

public class CaseC {
    public void query(Connection conn, String id) throws Exception {
        String sql = "SELECT * FROM t WHERE id = " + id;
        Statement s = conn.createStatement();
        ResultSet rs = s.executeQuery(sql);
    }
}
''')
    app_c, _, chg_c = ApplicationRemediator.apply_source_actions(src_c, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_c
    with open(file_c) as f:
        content_c = f.read()
    assert "import java.sql.PreparedStatement;" not in content_c

    # CASE D: package declaration + no imports -> import inserted after package declaration
    src_d = str(tmpdir.mkdir("import_case_d"))
    file_d = os.path.join(src_d, "CaseD.java")
    with open(file_d, "w") as f:
        f.write('''package com.example.noimports;

public class CaseD {
    public void query(Connection conn, String id) throws Exception {
        String sql = "SELECT * FROM t WHERE id = " + id;
        Statement s = conn.createStatement();
        ResultSet rs = s.executeQuery(sql);
    }
}
''')
    app_d, _, chg_d = ApplicationRemediator.apply_source_actions(src_d, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_d
    with open(file_d) as f:
        content_d = f.read()
    assert content_d.count("import java.sql.PreparedStatement;") == 1
    lines_d = content_d.splitlines()
    pkg_idx = next(i for i, l in enumerate(lines_d) if "package com.example.noimports;" in l)
    prep_idx = next(i for i, l in enumerate(lines_d) if "import java.sql.PreparedStatement;" in l)
    class_idx = next(i for i, l in enumerate(lines_d) if "public class CaseD" in l)
    assert pkg_idx < prep_idx < class_idx

    # CASE E: no package/import section -> import inserted before class declaration
    src_e = str(tmpdir.mkdir("import_case_e"))
    file_e = os.path.join(src_e, "CaseE.java")
    with open(file_e, "w") as f:
        f.write('''public class CaseE {
    public void query(Connection conn, String id) throws Exception {
        String sql = "SELECT * FROM t WHERE id = " + id;
        Statement s = conn.createStatement();
        ResultSet rs = s.executeQuery(sql);
    }
}
''')
    app_e, _, chg_e = ApplicationRemediator.apply_source_actions(src_e, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert "ACT_PARAMETERIZE_SQL_QUERIES" in app_e
    with open(file_e) as f:
        content_e = f.read()
    assert content_e.count("import java.sql.PreparedStatement;") == 1
    lines_e = content_e.splitlines()
    prep_idx_e = next(i for i, l in enumerate(lines_e) if "import java.sql.PreparedStatement;" in l)
    class_idx_e = next(i for i, l in enumerate(lines_e) if "public class CaseE" in l)
    assert prep_idx_e < class_idx_e

    # CASE F: unsupported SQL safe-skip -> no PreparedStatement import added
    src_f = str(tmpdir.mkdir("import_case_f"))
    file_f = os.path.join(src_f, "CaseF.java")
    with open(file_f, "w") as f:
        f.write('''package com.example;

import java.sql.Connection;
import java.sql.Statement;

public class CaseF {
    public void complexQuery(Connection conn, String a, String b, String c) throws Exception {
        StringBuilder sb = new StringBuilder();
        sb.append("SELECT * FROM t WHERE a=").append(a);
        Statement s = conn.createStatement();
        s.execute(sb.toString());
    }
}
''')
    app_f, skp_f, chg_f = ApplicationRemediator.apply_source_actions(src_f, ["ACT_PARAMETERIZE_SQL_QUERIES"])
    assert len(chg_f) == 0
    with open(file_f) as f:
        content_f = f.read()
    assert "import java.sql.PreparedStatement;" not in content_f
