import os
import time
import json
import tempfile
from typing import List, Dict, Any, Tuple

# Ensure JWT secret is set
if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "benchmark-security-key-phase6a5"

from backend.app.engines.terraform_cli import TerraformCLI
from backend.app.engines.terraform_plan_adapter import TerraformPlanAdapter
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
from benchmarks.common import get_smoke_dir, write_csv

SCALE_COLUMNS = [
    "resource_count_requested",
    "resource_count_planned",
    "source_bytes",
    "init_ms",
    "validate_ms",
    "plan_ms",
    "show_ms",
    "adapter_ms",
    "opa_ms",
    "total_ms",
    "plan_bytes",
    "evidence_bytes",
    "success",
    "error"
]

PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "engines", ".terraform_providers"))

def generate_scale_hcl(resource_count: int) -> str:
    """
    Generates deterministic Terraform HCL configuration with N independent
    aws_cloudwatch_log_group resources. Offline mock provider settings ensure
    zero external cloud dependencies.
    """
    blocks = [
        '''provider "aws" {
  region                      = "us-east-1"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
  access_key                  = "mock"
  secret_key                  = "mock"
}'''
    ]
    for i in range(resource_count):
        blocks.append(f'''resource "aws_cloudwatch_log_group" "log_{i}" {{
  name              = "log-group-{i}"
  retention_in_days = 180
}}''')
    return "\n\n".join(blocks) + "\n"

def execute_scale_step(resource_count: int) -> Dict[str, Any]:
    """
    Executes real stage-by-stage native Terraform and OPA pipeline without apply/destroy.
    Records granular wall-clock stage timings and payload byte sizes.
    """
    hcl_content = generate_scale_hcl(resource_count)
    source_bytes = len(hcl_content.encode("utf-8"))

    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "main.tf"), "w") as f:
            f.write(hcl_content)

        t_total_0 = time.perf_counter()
        err = "None"
        success = True

        # 1. terraform init
        t_init_0 = time.perf_counter()
        init_res = TerraformCLI._run_cmd(
            ["terraform", "init", "-input=false", "-no-color", "-backend=false", f"-plugin-dir={PLUGIN_DIR}"],
            cwd=td,
            timeout_sec=30
        )
        init_ms = round((time.perf_counter() - t_init_0) * 1000, 2)
        if init_res.returncode != 0:
            success = False
            err = f"INIT_FAILED: {init_res.stderr.strip()[:100]}"

        # 2. terraform validate -json
        t_val_0 = time.perf_counter()
        val_res = TerraformCLI._run_cmd(["terraform", "validate", "-json"], cwd=td, timeout_sec=15)
        validate_ms = round((time.perf_counter() - t_val_0) * 1000, 2)
        if val_res.returncode != 0:
            success = False
            err = f"VALIDATE_FAILED: {val_res.stderr.strip()[:100]}"

        # 3. terraform plan -out=tfplan (NO APPLY)
        t_plan_0 = time.perf_counter()
        plan_res = TerraformCLI._run_cmd(
            ["terraform", "plan", "-input=false", "-refresh=false", "-lock=false", "-no-color", "-out=tfplan"],
            cwd=td,
            timeout_sec=45
        )
        plan_ms = round((time.perf_counter() - t_plan_0) * 1000, 2)
        if plan_res.returncode != 0:
            success = False
            err = f"PLAN_FAILED: {plan_res.stderr.strip()[:100]}"

        # 4. terraform show -json tfplan
        t_show_0 = time.perf_counter()
        show_res = TerraformCLI._run_cmd(["terraform", "show", "-json", "tfplan"], cwd=td, timeout_sec=20)
        show_ms = round((time.perf_counter() - t_show_0) * 1000, 2)

        plan_bytes = len(show_res.stdout.encode("utf-8"))
        try:
            plan_json = json.loads(show_res.stdout)
        except json.JSONDecodeError:
            plan_json = {}
            success = False
            err = "SHOW_JSON_DECODE_ERROR"

        # Count planned managed resources
        planned_resources = [r for r in plan_json.get("resource_changes", []) if r.get("mode") == "managed"]
        resource_count_planned = len(planned_resources)

        # 5. TerraformPlanAdapter
        t_adapt_0 = time.perf_counter()
        adapted_plan = TerraformPlanAdapter.adapt(plan_json)
        adapter_ms = round((time.perf_counter() - t_adapt_0) * 1000, 2)

        # 6. OPAPolicyEvaluator
        t_opa_0 = time.perf_counter()
        violations = OPAPolicyEvaluator.evaluate_terraform_plan(adapted_plan)
        opa_ms = round((time.perf_counter() - t_opa_0) * 1000, 2)

        total_ms = round((time.perf_counter() - t_total_0) * 1000, 2)

        # Evidence bytes calculation
        evidence_payload = {
            "resource_count": resource_count,
            "violations": violations,
            "adapted_plan": adapted_plan
        }
        evidence_bytes = len(json.dumps(evidence_payload, sort_keys=True).encode("utf-8"))

        return {
            "resource_count_requested": resource_count,
            "resource_count_planned": resource_count_planned,
            "source_bytes": source_bytes,
            "init_ms": init_ms,
            "validate_ms": validate_ms,
            "plan_ms": plan_ms,
            "show_ms": show_ms,
            "adapter_ms": adapter_ms,
            "opa_ms": opa_ms,
            "total_ms": total_ms,
            "plan_bytes": plan_bytes,
            "evidence_bytes": evidence_bytes,
            "success": success,
            "error": err
        }

def run_scale(smoke: bool = False, out_dir: str = None) -> List[List[Any]]:
    """Runs the real scaling benchmark across controlled resource counts and outputs to scale.csv."""
    if out_dir is None:
        out_dir = get_smoke_dir()
    
    # Development smoke: 1 and 10 resources only
    resource_counts = [1, 10] if smoke else [1, 10, 25, 50, 100]
    print(f"Executing real scale benchmark across resource counts: {resource_counts}...")

    rows = []
    for count in resource_counts:
        print(f"  -> Testing scale for {count} resources...")
        res = execute_scale_step(count)
        row = [
            res["resource_count_requested"],
            res["resource_count_planned"],
            res["source_bytes"],
            res["init_ms"],
            res["validate_ms"],
            res["plan_ms"],
            res["show_ms"],
            res["adapter_ms"],
            res["opa_ms"],
            res["total_ms"],
            res["plan_bytes"],
            res["evidence_bytes"],
            res["success"],
            res["error"]
        ]
        rows.append(row)
        print(f"     ✓ Requested {count} -> Planned {res['resource_count_planned']} | Total: {res['total_ms']}ms | Plan: {res['plan_bytes']} bytes")

    csv_path = f"{out_dir}/scale.csv"
    write_csv(csv_path, SCALE_COLUMNS, rows)
    print(f"Wrote {len(rows)} real scale rows to {csv_path}")

    return rows

if __name__ == "__main__":
    run_scale(smoke=True)
