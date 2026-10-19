import os
import time
import shutil
import tempfile
from typing import List, Dict, Any, Tuple
from fastapi.testclient import TestClient

# Ensure JWT secret is set
if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "benchmark-security-key-phase6a5"

from backend.app.main import app
from backend.app.engines.terraform_cli import TerraformCLI
from backend.app.engines.terraform_plan_adapter import TerraformPlanAdapter
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
from backend.app.engines.terraform_engine import TerraformEngine
from backend.app.engines.rl_remediator import QLearningRemediationAgent
from backend.app.db.models import Project, EvaluationRun, Deployment, AuditLog
from backend.app.api.v1.audit import verify_audit_chain
from benchmarks.common import get_smoke_dir, write_csv
from benchmarks.security_helpers import isolated_test_db, get_auth_header, create_test_user
from benchmarks.stats_helpers import calculate_summary_stats

# Memory fallbacks for missing columns in production models to avoid AttributeError
Project.infrastructure_hash = None
EvaluationRun.infrastructure_hash = None
EvaluationRun.plan_hash = None

PERFORMANCE_COLUMNS = [
    "operation",
    "iteration",
    "warmup",
    "duration_ms",
    "sample_context",
    "success",
    "error"
]

REPRESENTATIVE_FIXTURE = "benchmarks/terraform/compliant/cw-ret-literal-pass.tf"

def measure_native_terraform(reps: int = 3) -> List[List[Any]]:
    """Measures real native Terraform pipeline (init, validate, plan, show, adapt, OPA)."""
    rows = []
    with open(REPRESENTATIVE_FIXTURE, "r") as f:
        fixture_content = f.read()

    # 1 warm-up + reps measured iterations
    for it in range(reps + 1):
        is_warmup = (it == 0)
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "main.tf"), "w") as tf_file:
                tf_file.write(fixture_content)

            t0 = time.perf_counter()
            err = "None"
            success = True
            try:
                cli_res = TerraformCLI.generate_plan_json(td)
                if not cli_res.success:
                    success = False
                    err = cli_res.failure_stage
                else:
                    adapted = TerraformPlanAdapter.adapt(cli_res.plan_json)
                    violations = OPAPolicyEvaluator.evaluate_terraform_plan(adapted)
            except Exception as e:
                success = False
                err = str(e)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)

            rows.append([
                "native_terraform",
                it,
                is_warmup,
                duration_ms,
                "fixture=cw-ret-literal-pass",
                success,
                err
            ])
    return rows

def measure_synthetic_terraform(reps: int = 5) -> List[List[Any]]:
    """Measures synthetic regex-based Terraform parser + OPA evaluation."""
    rows = []
    with open(REPRESENTATIVE_FIXTURE, "r") as f:
        fixture_content = f.read()

    for it in range(reps + 1):
        is_warmup = (it == 0)
        t0 = time.perf_counter()
        err = "None"
        success = True
        try:
            synth_plan = TerraformEngine.hcl_to_plan_json(fixture_content)
            violations = OPAPolicyEvaluator.evaluate_terraform_plan(synth_plan)
        except Exception as e:
            success = False
            err = str(e)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        rows.append([
            "synthetic_terraform",
            it,
            is_warmup,
            duration_ms,
            "fixture=cw-ret-literal-pass",
            success,
            err
        ])
    return rows

def measure_opa_only(reps: int = 5) -> List[List[Any]]:
    """Measures OPA evaluation directly on a pre-generated canonical plan (no Terraform parsing)."""
    rows = []
    # Pre-generate canonical plan once
    with tempfile.TemporaryDirectory() as td:
        with open(REPRESENTATIVE_FIXTURE, "r") as f:
            content = f.read()
        with open(os.path.join(td, "main.tf"), "w") as f:
            f.write(content)
        cli_res = TerraformCLI.generate_plan_json(td)
        canonical_plan = TerraformPlanAdapter.adapt(cli_res.plan_json)

    for it in range(reps + 1):
        is_warmup = (it == 0)
        t0 = time.perf_counter()
        err = "None"
        success = True
        try:
            violations = OPAPolicyEvaluator.evaluate_terraform_plan(canonical_plan)
        except Exception as e:
            success = False
            err = str(e)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        rows.append([
            "opa_policy_evaluation",
            it,
            is_warmup,
            duration_ms,
            "target=data.regulacloud",
            success,
            err
        ])
    return rows

def measure_rl_inference(reps: int = 10) -> List[List[Any]]:
    """Measures pure recommendation/inference latency of a pre-trained Q-learning agent."""
    rows = []
    agent = QLearningRemediationAgent()
    agent.train_simulator(episodes=150)  # Training excluded from inference timing

    active_violations = ["CTRL-AWS-RDS-NO-PUBLIC", "CTRL-AWS-S3-ENC"]

    for it in range(reps + 1):
        is_warmup = (it == 0)
        t0 = time.perf_counter()
        err = "None"
        success = True
        try:
            plan = agent.recommend_remediations(active_violations)
            success = (len(plan) > 0)
        except Exception as e:
            success = False
            err = str(e)
        duration_ms = round((time.perf_counter() - t0) * 1000, 4)

        rows.append([
            "rl_remediation_inference",
            it,
            is_warmup,
            duration_ms,
            "active_violations=2",
            success,
            err
        ])
    return rows

def measure_remediation_mutation(reps: int = 5) -> List[List[Any]]:
    """Measures pure in-memory TerraformEngine HCL regex mutation cost."""
    rows = []
    broken_hcl = 'resource "aws_db_instance" "test" {\n  publicly_accessible = true\n  storage_encrypted = false\n}\n'

    for it in range(reps + 1):
        is_warmup = (it == 0)
        t0 = time.perf_counter()
        err = "None"
        success = True
        try:
            new_hcl, applied, skipped = TerraformEngine.apply_rl_actions(broken_hcl, ["ACT_DISABLE_RDS_PUBLIC"])
            success = ("ACT_DISABLE_RDS_PUBLIC" in applied)
        except Exception as e:
            success = False
            err = str(e)
        duration_ms = round((time.perf_counter() - t0) * 1000, 4)

        rows.append([
            "terraform_remediation_mutation",
            it,
            is_warmup,
            duration_ms,
            "action=ACT_DISABLE_RDS_PUBLIC",
            success,
            err
        ])
    return rows

def measure_remediation_plus_verification(reps: int = 3) -> List[List[Any]]:
    """Measures full remediation cycle: HCL mutation + native re-evaluation pipeline."""
    rows = []
    broken_hcl = 'resource "aws_db_instance" "test" {\n  instance_class = "db.t3.micro"\n  allocated_storage = 20\n  publicly_accessible = true\n}\n'

    for it in range(reps + 1):
        is_warmup = (it == 0)
        t0 = time.perf_counter()
        err = "None"
        success = True
        try:
            new_hcl, applied, skipped = TerraformEngine.apply_rl_actions(broken_hcl, ["ACT_DISABLE_RDS_PUBLIC"])
            with tempfile.TemporaryDirectory() as td:
                with open(os.path.join(td, "main.tf"), "w") as f:
                    f.write(new_hcl)
                cli_res = TerraformCLI.generate_plan_json(td)
                if not cli_res.success:
                    success = False
                    err = cli_res.failure_stage
                else:
                    adapted = TerraformPlanAdapter.adapt(cli_res.plan_json)
                    violations = OPAPolicyEvaluator.evaluate_terraform_plan(adapted)
        except Exception as e:
            success = False
            err = str(e)
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)

        rows.append([
            "remediation_plus_native_revalidation",
            it,
            is_warmup,
            duration_ms,
            "action=ACT_DISABLE_RDS_PUBLIC;native_revalidation",
            success,
            err
        ])
    return rows

def measure_api_endpoints(topo_reps: int = 10, dash_reps: int = 10, audit_reps: int = 10) -> List[List[Any]]:
    """Measures API endpoint latencies (Topology, Dashboard, Audit Verification) on an isolated database."""
    rows = []
    with isolated_test_db() as (engine, SessionLocal, db_path):
        session = SessionLocal()
        admin = create_test_user(session, "admin", "ADMIN")

        # 1. Setup deterministic project and evaluation run with pre-generated plan
        dummy_plan = {
            "planned_values": {
                "root_module": {
                    "resources": [
                        {"address": "aws_s3_bucket.b", "type": "aws_s3_bucket", "name": "b"},
                        {"address": "aws_db_instance.db", "type": "aws_db_instance", "name": "db"}
                    ]
                }
            },
            "configuration": {
                "root_module": {
                    "resources": [
                        {"type": "aws_s3_bucket", "name": "b"},
                        {"type": "aws_db_instance", "name": "db"}
                    ]
                }
            }
        }
        project = Project(
            id="proj-perf-topo",
            name="Topology Perf Project",
            organization="GovOrg",
            sector="Healthcare",
            jurisdiction="India",
            environment="production",
            cloud_provider="AWS",
            aws_region="ap-south-1",
            owner=admin.username,
            status="Protected",
            compliance_score=95.0
        )
        session.add(project)

        eval_run = EvaluationRun(
            id="eval-run-perf-topo",
            project_id=project.id,
            trigger_type="PRE_DEPLOY",
            overall_status="PASS",
            compliance_score=95.0,
            passed_count=2,
            failed_count=0,
            unknown_count=0,
            not_applicable_count=0,
            evidence_payload={"native_plan_json": dummy_plan, "plan_hash": "dummy_plan_hash_123"},
            evidence_hash="evidence_hash_123"
        )
        session.add(eval_run)

        # 2. Setup deployments
        deployment = Deployment(
            id="dep-perf-test",
            project_id=project.id,
            status="SUCCESS",
            evaluation_run_id=eval_run.id,
            logs=[]
        )
        session.add(deployment)

        # 3. Setup audit chain of length 10
        for i in range(10):
            AuditLog.create_entry(
                session=session,
                actor="admin",
                action=f"BENCHMARK_ACTION_{i}",
                resource_type="PROJECT",
                resource_id=project.id,
                severity="Low",
                details={"step": i}
            )
        session.commit()

        client = TestClient(app)
        headers = get_auth_header("admin", "ADMIN")

        # Measure Topology Endpoint (NO Terraform executed during measurement)
        for it in range(topo_reps + 1):
            is_warmup = (it == 0)
            t0 = time.perf_counter()
            res = client.get(f"/api/v1/projects/{project.id}/infrastructure/topology", headers=headers)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            success = (res.status_code == 200)
            err = "None" if success else f"Status {res.status_code}"

            rows.append([
                "api_topology",
                it,
                is_warmup,
                duration_ms,
                f"project_id={project.id}",
                success,
                err
            ])

        # Measure Dashboard Stats Endpoint
        for it in range(dash_reps + 1):
            is_warmup = (it == 0)
            t0 = time.perf_counter()
            res = client.get("/api/v1/dashboard/stats", headers=headers)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            success = (res.status_code == 200)
            err = "None" if success else f"Status {res.status_code}"

            rows.append([
                "api_dashboard",
                it,
                is_warmup,
                duration_ms,
                "endpoint=/dashboard/stats",
                success,
                err
            ])

        # Measure Audit Chain Verification (Chain length = 10)
        for it in range(audit_reps + 1):
            is_warmup = (it == 0)
            t0 = time.perf_counter()
            verify_res = verify_audit_chain(current_user=None, db=session)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            success = verify_res.get("valid", False)
            err = "None" if success else str(verify_res.get("error"))

            rows.append([
                "audit_verify_chain",
                it,
                is_warmup,
                duration_ms,
                "chain_length=10",
                success,
                err
            ])

        session.close()

    return rows

def run_performance(smoke: bool = False, out_dir: str = None) -> List[List[Any]]:
    """Runs all real performance benchmark operations and outputs to performance.csv."""
    if out_dir is None:
        out_dir = get_smoke_dir()
    print("Executing real performance benchmark harness...")

    rows: List[List[Any]] = []

    print("  -> Measuring Native Terraform (1 warmup + 3 measured)...")
    rows.extend(measure_native_terraform(reps=3))

    print("  -> Measuring Synthetic Terraform (1 warmup + 5 measured)...")
    rows.extend(measure_synthetic_terraform(reps=5))

    print("  -> Measuring OPA Policy Evaluation (1 warmup + 5 measured)...")
    rows.extend(measure_opa_only(reps=5))

    print("  -> Measuring RL Recommendation Inference (1 warmup + 10 measured)...")
    rows.extend(measure_rl_inference(reps=10))

    print("  -> Measuring Terraform Mutation (1 warmup + 5 measured)...")
    rows.extend(measure_remediation_mutation(reps=5))

    print("  -> Measuring Remediation + Native Re-validation (1 warmup + 3 measured)...")
    rows.extend(measure_remediation_plus_verification(reps=3))

    print("  -> Measuring API Endpoints: Topology, Dashboard, Audit (1 warmup + 10 measured each)...")
    rows.extend(measure_api_endpoints(topo_reps=10, dash_reps=10, audit_reps=10))

    csv_path = f"{out_dir}/performance.csv"
    write_csv(csv_path, PERFORMANCE_COLUMNS, rows)
    print(f"Wrote {len(rows)} real performance measurements to {csv_path}")

    return rows

if __name__ == "__main__":
    run_performance(smoke=True)
