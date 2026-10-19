import os
import time
import zipfile
import tempfile
import threading
from typing import Dict, Any, List, Tuple
from fastapi.testclient import TestClient
from fastapi import HTTPException

# Ensure JWT secret is set
if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "benchmark-security-key-phase6a5"

from backend.app.main import app
from backend.app.api.v1.projects import extract_safe_zip
from backend.app.api.v1.audit import verify_audit_chain
from backend.app.db.models import Project, User, Deployment, AuditLog
from benchmarks.common import get_smoke_dir, write_csv
from benchmarks.security_helpers import isolated_test_db, get_auth_header, create_test_user, verify_normal_db_untouched

SECURITY_COLUMNS = [
    "scenario",
    "expected_status",
    "actual_status",
    "expected_security_outcome",
    "actual_security_outcome",
    "passed",
    "duration_ms",
    "error"
]

def run_unauthenticated_scenario(expected_status: int = 401) -> Dict[str, Any]:
    """Tests that unauthenticated requests to protected endpoints return HTTP 401."""
    t0 = time.perf_counter()
    client = TestClient(app)
    res = client.get("/api/v1/deployments")
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    
    actual_status = res.status_code
    actual_outcome = "DENIED_UNAUTHENTICATED" if actual_status == 401 else f"STATUS_{actual_status}"
    passed = (actual_status == expected_status)
    err = "None" if passed else f"Expected {expected_status}, got {actual_status}"

    return {
        "scenario": "unauthenticated_protected_endpoint",
        "expected_status": expected_status,
        "actual_status": actual_status,
        "expected_security_outcome": "DENIED_UNAUTHENTICATED",
        "actual_security_outcome": actual_outcome,
        "passed": passed,
        "duration_ms": duration_ms,
        "error": err
    }

def run_cross_project_scenario(expected_status: int = 403) -> Dict[str, Any]:
    """Tests that user A is forbidden (403) from accessing projects owned by user B."""
    t0 = time.perf_counter()
    with isolated_test_db() as (engine, SessionLocal, db_path):
        session = SessionLocal()
        try:
            user_a = create_test_user(session, "operator_a", "USER")
            user_b = create_test_user(session, "operator_b", "USER")
            
            project_b = Project(
                id="proj-user-b-private",
                name="Project Owned by B",
                organization="OrgB",
                sector="Finance",
                environment="production",
                cloud_provider="AWS",
                aws_region="ap-south-1",
                owner=user_b.username,
                status="Protected",
                hcl_content='resource "aws_s3_bucket" "b" {}\n'
            )
            session.add(project_b)
            session.commit()

            client = TestClient(app)
            headers_a = get_auth_header("operator_a", "USER")
            res = client.get(f"/api/v1/projects/{project_b.id}/hcl", headers=headers_a)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)

            actual_status = res.status_code
            actual_outcome = "FORBIDDEN_CROSS_PROJECT" if actual_status == 403 else f"STATUS_{actual_status}"
            passed = (actual_status == expected_status)
            err = "None" if passed else f"Expected {expected_status}, got {actual_status}"

            return {
                "scenario": "cross_project_access",
                "expected_status": expected_status,
                "actual_status": actual_status,
                "expected_security_outcome": "FORBIDDEN_CROSS_PROJECT",
                "actual_security_outcome": actual_outcome,
                "passed": passed,
                "duration_ms": duration_ms,
                "error": err
            }
        finally:
            session.close()

def run_user_apply_scenario(expected_status: int = 403) -> Dict[str, Any]:
    """Tests that a standard non-admin USER role is forbidden (403) from applying deployments."""
    t0 = time.perf_counter()
    with isolated_test_db() as (engine, SessionLocal, db_path):
        session = SessionLocal()
        try:
            user = create_test_user(session, "operator_user", "USER")
            deployment = Deployment(
                id="dep-user-apply-test",
                project_id="proj-fake",
                status="AWAITING_APPROVAL",
                logs=[]
            )
            session.add(deployment)
            session.commit()

            client = TestClient(app)
            headers_user = get_auth_header("operator_user", "USER")
            res = client.post(f"/api/v1/deployments/{deployment.id}/apply", headers=headers_user)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)

            actual_status = res.status_code
            actual_outcome = "FORBIDDEN_NON_ADMIN_APPLY" if actual_status == 403 else f"STATUS_{actual_status}"
            passed = (actual_status == expected_status)
            err = "None" if passed else f"Expected {expected_status}, got {actual_status}"

            return {
                "scenario": "user_deployment_apply",
                "expected_status": expected_status,
                "actual_status": actual_status,
                "expected_security_outcome": "FORBIDDEN_NON_ADMIN_APPLY",
                "actual_security_outcome": actual_outcome,
                "passed": passed,
                "duration_ms": duration_ms,
                "error": err
            }
        finally:
            session.close()

def run_zip_traversal_scenario() -> Dict[str, Any]:
    """Tests that directory traversal members (../evil.txt) are not extracted outside the destination root."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        zip_path = os.path.join(td, "traversal.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../evil.txt", "evil_content")
            zf.writestr("legit.txt", "safe_content")

        extract_dir = os.path.join(td, "extract_dest")
        os.makedirs(extract_dir, exist_ok=True)

        extract_safe_zip(zip_path, extract_dir)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        escaped_file = os.path.join(td, "evil.txt")
        outside_written = os.path.exists(escaped_file)
        legit_written = os.path.exists(os.path.join(extract_dir, "legit.txt"))

        actual_outcome = "OUTSIDE_WRITE_PREVENTED" if (not outside_written and legit_written) else "TRAVERSAL_BREACH"
        passed = (not outside_written and legit_written)
        err = "None" if passed else "File escaped extraction directory"

        return {
            "scenario": "zip_path_traversal",
            "expected_status": 200,
            "actual_status": 200,
            "expected_security_outcome": "OUTSIDE_WRITE_PREVENTED",
            "actual_security_outcome": actual_outcome,
            "passed": passed,
            "duration_ms": duration_ms,
            "error": err
        }

def run_zip_symlink_scenario() -> Dict[str, Any]:
    """Tests that symbolic links in ZIP archives are disallowed to prevent symlink traversal escaping."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        zip_path = os.path.join(td, "symlink.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zinfo = zipfile.ZipInfo("symlink_entry")
            zinfo.create_system = 3  # Unix
            zinfo.external_attr = 0xA1ED0000  # Symlink bitmask
            zf.writestr(zinfo, "/etc/passwd")

        extract_dir = os.path.join(td, "extract_dest")
        os.makedirs(extract_dir, exist_ok=True)

        extract_safe_zip(zip_path, extract_dir)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        symlink_path = os.path.join(extract_dir, "symlink_entry")
        symlink_created = os.path.islink(symlink_path) or os.path.exists(symlink_path)

        actual_outcome = "SYMLINK_DISALLOWED" if not symlink_created else "SYMLINK_CREATED"
        passed = not symlink_created
        err = "None" if passed else "Symlink was created during extraction"

        return {
            "scenario": "zip_symlink",
            "expected_status": 200,
            "actual_status": 200,
            "expected_security_outcome": "SYMLINK_DISALLOWED",
            "actual_security_outcome": actual_outcome,
            "passed": passed,
            "duration_ms": duration_ms,
            "error": err
        }

def run_zip_limits_scenario() -> Dict[str, Any]:
    """Tests that ZIP archive exceeding the 1000-file safety limit is rejected with HTTP 400."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        zip_path = os.path.join(td, "many_files.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(1001):
                zf.writestr(f"item_{i}.txt", "x")

        extract_dir = os.path.join(td, "extract_dest")
        os.makedirs(extract_dir, exist_ok=True)

        actual_status = 200
        detail = ""
        try:
            extract_safe_zip(zip_path, extract_dir)
        except HTTPException as e:
            actual_status = e.status_code
            detail = str(e.detail)

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        actual_outcome = "FILE_COUNT_LIMIT_ENFORCED" if actual_status == 400 else f"STATUS_{actual_status}"
        passed = (actual_status == 400)
        err = detail if not passed else "None"

        return {
            "scenario": "zip_file_count_limit",
            "expected_status": 400,
            "actual_status": actual_status,
            "expected_security_outcome": "FILE_COUNT_LIMIT_ENFORCED",
            "actual_security_outcome": actual_outcome,
            "passed": passed,
            "duration_ms": duration_ms,
            "error": err
        }

def run_audit_tamper_scenario() -> Dict[str, Any]:
    """Tests that tampering with a committed audit log entry breaks the SHA-256 chain and is detected."""
    t0 = time.perf_counter()
    with isolated_test_db() as (engine, SessionLocal, db_path):
        session = SessionLocal()
        try:
            # Create legitimate audit log chain
            for i in range(3):
                AuditLog.create_entry(
                    session=session,
                    actor=f"actor_{i}",
                    action=f"ACTION_{i}",
                    resource_type="PROJECT",
                    resource_id=f"proj_{i}",
                    severity="Low",
                    details={"index": i}
                )

            # 1. Verify chain before tampering
            res_clean = verify_audit_chain(current_user=None, db=session)
            valid_before = res_clean.get("valid", False)

            # 2. Tamper historical entry
            entry_2 = session.query(AuditLog).filter(AuditLog.id == 2).first()
            entry_2.details = {"index": 2, "tampered_attribute": "unauthorized"}
            session.commit()

            # 3. Verify chain after tampering
            res_tampered = verify_audit_chain(current_user=None, db=session)
            valid_after = res_tampered.get("valid", True)
            tamper_error = res_tampered.get("error", "")

            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            actual_outcome = "TAMPER_DETECTED_INVALID_CHAIN" if (valid_before and not valid_after) else "TAMPER_UNDETECTED"
            passed = (valid_before and not valid_after)
            err = tamper_error if passed else "Tamper was not detected by audit verification"

            return {
                "scenario": "audit_tamper",
                "expected_status": 200,
                "actual_status": 200,
                "expected_security_outcome": "TAMPER_DETECTED_INVALID_CHAIN",
                "actual_security_outcome": actual_outcome,
                "passed": passed,
                "duration_ms": duration_ms,
                "error": err.replace(",", ";")
            }
        finally:
            session.close()

def run_audit_concurrency_scenario() -> Dict[str, Any]:
    """Tests that concurrent audit log appends maintain lock serialization and preserve chain integrity."""
    t0 = time.perf_counter()
    with isolated_test_db() as (engine, SessionLocal, db_path):
        session = SessionLocal()
        try:
            def append_worker(idx: int):
                AuditLog.create_entry(
                    session=session,
                    actor=f"concurrent_worker_{idx}",
                    action="CONCURRENT_APPEND",
                    resource_type="AUDIT",
                    resource_id=f"worker_{idx}",
                    severity="Low",
                    details={"worker_id": idx}
                )

            threads = [threading.Thread(target=append_worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            res = verify_audit_chain(current_user=None, db=session)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)

            chain_valid = res.get("valid", False)
            entries_checked = res.get("entries_checked", 0)
            passed = (chain_valid and entries_checked == 5)
            actual_outcome = "CONCURRENT_CHAIN_INTACT" if passed else "CONCURRENCY_BROKE_CHAIN"

            return {
                "scenario": "audit_concurrency",
                "expected_status": 200,
                "actual_status": 200,
                "expected_security_outcome": "CONCURRENT_CHAIN_INTACT",
                "actual_security_outcome": actual_outcome,
                "passed": passed,
                "duration_ms": duration_ms,
                "error": res.get("error") or "None"
            }
        finally:
            session.close()

def run_security(smoke: bool = False) -> List[List[Any]]:
    """Runs the real security and isolation benchmark scenarios and outputs results to CSV."""
    out_dir = get_smoke_dir()

    scenarios = [
        run_unauthenticated_scenario,
        run_cross_project_scenario,
        run_user_apply_scenario,
        run_zip_traversal_scenario,
        run_zip_symlink_scenario,
        run_zip_limits_scenario,
        run_audit_tamper_scenario,
        run_audit_concurrency_scenario
    ]

    rows = []
    print(f"Executing {len(scenarios)} real security benchmark scenarios...")
    for fn in scenarios:
        res = fn()
        row = [
            res["scenario"],
            res["expected_status"],
            res["actual_status"],
            res["expected_security_outcome"],
            res["actual_security_outcome"],
            res["passed"],
            res["duration_ms"],
            str(res["error"]).replace(",", ";")
        ]
        rows.append(row)
        print(f"  ✓ {res['scenario']}: status={res['actual_status']} outcome={res['actual_security_outcome']} passed={res['passed']} ({res['duration_ms']}ms)")

    csv_path = f"{out_dir}/security.csv"
    write_csv(csv_path, SECURITY_COLUMNS, rows)
    print(f"Wrote {len(rows)} real security rows to {csv_path}")
    return rows

if __name__ == "__main__":
    run_security(smoke=True)
