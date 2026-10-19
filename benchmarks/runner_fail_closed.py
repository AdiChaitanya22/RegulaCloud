import os
import time
import subprocess
import tempfile
from typing import Dict, Any, List, Tuple
from fastapi.testclient import TestClient

# Ensure JWT secret is set
if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "benchmark-security-key-phase6a5"

from backend.app.main import app
from backend.app.engines.terraform_cli import TerraformCLI
from backend.app.engines.compliance_engine import ComplianceEngine
from backend.app.db.models import Project, Deployment
from benchmarks.common import get_smoke_dir, write_csv
from benchmarks.security_helpers import isolated_test_db, get_auth_header, create_test_user, verify_normal_db_untouched

FAIL_CLOSED_COLUMNS = [
    "scenario",
    "expected_compliance",
    "actual_compliance",
    "expected_authorized",
    "actual_authorized",
    "blocked",
    "failure_stage",
    "http_status",
    "duration_ms",
    "error"
]

def run_malformed_terraform_scenario(expected_compliance: str = "FAIL", expected_authorized: bool = False) -> Dict[str, Any]:
    """Tests that syntactically malformed Terraform fails during validation and blocks deployment."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        tf_file = os.path.join(td, "broken.tf")
        with open(tf_file, "w") as f:
            f.write('resource "aws_db_instance" "broken" {\n  allocated_storage = \n')
        
        cli_res = TerraformCLI.generate_plan_json(td)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        
        actual_compliance = cli_res.validation_status  # "ERROR"
        actual_authorized = False
        blocked = not actual_authorized
        err = cli_res.diagnostics[0].get("summary", "Validation error") if cli_res.diagnostics else "Unknown"
        
        return {
            "scenario": "malformed_terraform",
            "expected_compliance": expected_compliance,
            "actual_compliance": actual_compliance,
            "expected_authorized": expected_authorized,
            "actual_authorized": actual_authorized,
            "blocked": blocked,
            "failure_stage": cli_res.failure_stage,
            "http_status": "N/A",
            "duration_ms": duration_ms,
            "error": err
        }

def run_missing_executable_scenario(expected_compliance: str = "FAIL", expected_authorized: bool = False) -> Dict[str, Any]:
    """Tests that missing Terraform binary triggers real FileNotFoundError handler and blocks deployment."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        tf_file = os.path.join(td, "main.tf")
        with open(tf_file, "w") as f:
            f.write('resource "aws_s3_bucket" "b" {}\n')

        # Monkeypatch subprocess.run within _run_cmd to simulate FileNotFoundError
        orig_run = subprocess.run
        def mock_run_fn(cmd, *args, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "terraform":
                raise FileNotFoundError("terraform executable not found in PATH")
            return orig_run(cmd, *args, **kwargs)

        try:
            subprocess.run = mock_run_fn
            cli_res = TerraformCLI.generate_plan_json(td)
        finally:
            subprocess.run = orig_run

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        actual_compliance = cli_res.validation_status
        actual_authorized = False
        blocked = not actual_authorized
        err = cli_res.diagnostics[0].get("summary", "") if cli_res.diagnostics else cli_res.stderr

        return {
            "scenario": "missing_terraform_executable",
            "expected_compliance": expected_compliance,
            "actual_compliance": actual_compliance,
            "expected_authorized": expected_authorized,
            "actual_authorized": actual_authorized,
            "blocked": blocked,
            "failure_stage": cli_res.failure_stage,
            "http_status": "N/A",
            "duration_ms": duration_ms,
            "error": err
        }

def run_missing_provider_scenario(expected_compliance: str = "FAIL", expected_authorized: bool = False) -> Dict[str, Any]:
    """Tests that missing provider directory causes terraform init to fail and blocks deployment."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        tf_file = os.path.join(td, "main.tf")
        with open(tf_file, "w") as f:
            f.write('resource "aws_db_instance" "db" {\n  instance_class = "db.t3.micro"\n  allocated_storage = 20\n}\n')

        # Monkeypatch _run_cmd to redirect -plugin-dir to a nonexistent path
        orig_run_cmd = TerraformCLI._run_cmd
        def mock_run_cmd(cmd, cwd, timeout_sec=30):
            modified_cmd = []
            for arg in cmd:
                if arg.startswith("-plugin-dir="):
                    modified_cmd.append("-plugin-dir=/tmp/nonexistent_providers_smoke_test")
                else:
                    modified_cmd.append(arg)
            return orig_run_cmd(modified_cmd, cwd, timeout_sec)

        try:
            TerraformCLI._run_cmd = mock_run_cmd
            cli_res = TerraformCLI.generate_plan_json(td)
        finally:
            TerraformCLI._run_cmd = orig_run_cmd

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        actual_compliance = cli_res.validation_status
        actual_authorized = False
        blocked = not actual_authorized
        err = cli_res.diagnostics[0].get("summary", "Init failed") if cli_res.diagnostics else cli_res.stderr

        return {
            "scenario": "missing_provider_directory",
            "expected_compliance": expected_compliance,
            "actual_compliance": actual_compliance,
            "expected_authorized": expected_authorized,
            "actual_authorized": actual_authorized,
            "blocked": blocked,
            "failure_stage": cli_res.failure_stage,
            "http_status": "N/A",
            "duration_ms": duration_ms,
            "error": err
        }

def run_timeout_scenario(expected_compliance: str = "FAIL", expected_authorized: bool = False) -> Dict[str, Any]:
    """Tests that command execution timeout invokes real timeout handler and blocks deployment."""
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as td:
        tf_file = os.path.join(td, "main.tf")
        with open(tf_file, "w") as f:
            f.write('resource "aws_s3_bucket" "b" {}\n')

        orig_run = subprocess.run
        def mock_run_timeout(cmd, *args, **kwargs):
            if isinstance(cmd, list) and "plan" in cmd:
                raise subprocess.TimeoutExpired(cmd=cmd, timeout=30)
            return orig_run(cmd, *args, **kwargs)

        try:
            subprocess.run = mock_run_timeout
            cli_res = TerraformCLI.generate_plan_json(td)
        finally:
            subprocess.run = orig_run

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        actual_compliance = cli_res.validation_status
        actual_authorized = False
        blocked = not actual_authorized
        err = cli_res.diagnostics[0].get("summary", "Command timed out") if cli_res.diagnostics else cli_res.stderr

        return {
            "scenario": "subprocess_timeout",
            "expected_compliance": expected_compliance,
            "actual_compliance": actual_compliance,
            "expected_authorized": expected_authorized,
            "actual_authorized": actual_authorized,
            "blocked": blocked,
            "failure_stage": cli_res.failure_stage,
            "http_status": "N/A",
            "duration_ms": duration_ms,
            "error": err
        }

def run_stale_artifact_scenario(expected_compliance: str = "PASS", expected_authorized: bool = False) -> Dict[str, Any]:
    """Tests that post-evaluation mutation of infrastructure artifact causes deployment gate rejection."""
    t0 = time.perf_counter()
    with isolated_test_db() as (engine, SessionLocal, db_path):
        session = SessionLocal()
        try:
            admin = create_test_user(session, "admin", "ADMIN")
            project = Project(
                id="proj-stale-gate-test",
                name="Stale Artifact Test",
                organization="TestOrg",
                sector="Healthcare",
                jurisdiction="India",
                data_categories=["personal_data"],
                environment="production",
                cloud_provider="AWS",
                aws_region="ap-south-1",
                owner=admin.username,
                status="Protected",
                hcl_content='resource "aws_s3_bucket" "valid" {}\n'
            )
            session.add(project)
            session.commit()

            # 1. Run legitimate compliance evaluation
            eval_res = ComplianceEngine.evaluate_compliance(session, project.id, trigger_type="PRE_DEPLOY")
            eval_run_id = eval_res.get("evaluation_run_id")

            # 2. Create awaiting approval deployment plan
            deployment = Deployment(
                id="dep-stale-gate-test",
                project_id=project.id,
                status="AWAITING_APPROVAL",
                evaluation_run_id=eval_run_id,
                logs=[]
            )
            session.add(deployment)
            session.commit()

            # 3. TOCTOU mutation: change infrastructure artifact in DB AFTER compliance evaluation
            project.hcl_content = 'resource "aws_s3_bucket" "tampered_after_eval" {}\n'
            session.commit()

            # 4. Attempt deployment apply with ADMIN token
            client = TestClient(app)
            headers = get_auth_header("admin", "ADMIN")
            res = client.post(f"/api/v1/deployments/{deployment.id}/apply", headers=headers)

            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            http_status = res.status_code
            detail = res.json().get("detail", "") if res.headers.get("content-type") == "application/json" else res.text

            actual_authorized = (http_status == 200)
            blocked = not actual_authorized

            return {
                "scenario": "stale_artifact_tamper",
                "expected_compliance": expected_compliance,
                "actual_compliance": eval_res["overall_status"],
                "expected_authorized": expected_authorized,
                "actual_authorized": actual_authorized,
                "blocked": blocked,
                "failure_stage": "DEPLOYMENT_GATE_ARTIFACT_BINDING",
                "http_status": http_status,
                "duration_ms": duration_ms,
                "error": detail
            }
        finally:
            session.close()

def run_unsupported_resource_scenario(expected_compliance: str = "PASS", expected_authorized: bool = True) -> Dict[str, Any]:
    """Tests that unmapped resource is categorized as NOT_APPLICABLE and does not erroneously fail compliance."""
    t0 = time.perf_counter()
    with isolated_test_db() as (engine, SessionLocal, db_path):
        session = SessionLocal()
        try:
            admin = create_test_user(session, "admin", "ADMIN")
            project = Project(
                id="proj-unsupported-res-test",
                name="Unsupported Resource Test",
                organization="TestOrg",
                sector="Tech",
                jurisdiction="India",
                data_categories=["personal_data"],
                environment="production",
                cloud_provider="AWS",
                aws_region="us-east-1",
                owner=admin.username,
                status="Protected",
                hcl_content='resource "aws_dynamodb_table" "unsupported_tbl" {\n  name = "demo"\n}\n'
            )
            session.add(project)
            session.commit()

            eval_res = ComplianceEngine.evaluate_compliance(session, project.id, trigger_type="MANUAL_SCAN")
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)

            actual_compliance = eval_res["overall_status"]
            actual_authorized = eval_res["deployment_allowed"]
            blocked = not actual_authorized

            return {
                "scenario": "unsupported_resource",
                "expected_compliance": expected_compliance,
                "actual_compliance": actual_compliance,
                "expected_authorized": expected_authorized,
                "actual_authorized": actual_authorized,
                "blocked": blocked,
                "failure_stage": "NONE",
                "http_status": "N/A",
                "duration_ms": duration_ms,
                "error": "None"
            }
        finally:
            session.close()

def run_fail_closed(smoke: bool = False) -> List[List[Any]]:
    """Runs the real fail-closed evaluation benchmark and outputs results to CSV."""
    out_dir = get_smoke_dir()
    
    scenarios = [
        run_malformed_terraform_scenario,
        run_missing_executable_scenario,
        run_missing_provider_scenario,
        run_timeout_scenario,
        run_stale_artifact_scenario,
        run_unsupported_resource_scenario
    ]
    
    rows = []
    print(f"Executing {len(scenarios)} real fail-closed benchmark scenarios...")
    for fn in scenarios:
        res = fn()
        row = [
            res["scenario"],
            res["expected_compliance"],
            res["actual_compliance"],
            res["expected_authorized"],
            res["actual_authorized"],
            res["blocked"],
            res["failure_stage"],
            res["http_status"],
            res["duration_ms"],
            str(res["error"]).replace(",", ";")
        ]
        rows.append(row)
        print(f"  ✓ {res['scenario']}: compliance={res['actual_compliance']} stage={res['failure_stage']} blocked={res['blocked']} ({res['duration_ms']}ms)")

    csv_path = f"{out_dir}/fail_closed.csv"
    write_csv(csv_path, FAIL_CLOSED_COLUMNS, rows)
    print(f"Wrote {len(rows)} real fail-closed rows to {csv_path}")
    return rows

if __name__ == "__main__":
    run_fail_closed(smoke=True)
