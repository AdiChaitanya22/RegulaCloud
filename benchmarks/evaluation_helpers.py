import os
import sys
import time
import json
import re
import tempfile
from typing import Dict, Any, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app.engines.terraform_cli import TerraformCLI
from backend.app.engines.terraform_plan_adapter import TerraformPlanAdapter
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
from backend.app.engines.terraform_engine import TerraformEngine

def extract_feature(tags: List[str]) -> str:
    known = ["literal", "variable", "local", "conditional", "count", "for_each", "module"]
    for k in known:
        if k in tags:
            return k
    if "reference" in tags:
        return "resource_reference"
    if "nested" in tags:
        return "nested_block"
    return tags[0] if tags else "unknown"

def extract_resolved_value(resource_changes: List[Dict[str, Any]], control_id: str) -> str:
    if not resource_changes:
        return "None"
        
    if "RDS-NO-PUBLIC" in control_id:
        for r in resource_changes:
            if r.get("type") == "aws_db_instance":
                val = r.get("change", {}).get("after", {}).get("publicly_accessible")
                return str(val) if val is not None else "None"
    elif "RDS-STORAGE-ENC" in control_id:
        for r in resource_changes:
            if r.get("type") == "aws_db_instance":
                val = r.get("change", {}).get("after", {}).get("storage_encrypted")
                return str(val) if val is not None else "None"
    elif "LOG" in control_id:
        for r in resource_changes:
            if r.get("type") == "aws_cloudwatch_log_group":
                val = r.get("change", {}).get("after", {}).get("retention_in_days")
                return str(val) if val is not None else "None"
    elif "S3-ENC" in control_id:
        enc_configs = [r for r in resource_changes if r.get("type") == "aws_s3_bucket_server_side_encryption_configuration"]
        if enc_configs:
            rule = enc_configs[0].get("change", {}).get("after", {}).get("rule")
            sse = enc_configs[0].get("change", {}).get("after", {}).get("sse_algorithm")
            if sse:
                return str(sse)
            if rule and isinstance(rule, list) and len(rule) > 0:
                algo = rule[0].get("apply_server_side_encryption_by_default", [{}])[0].get("sse_algorithm")
                return str(algo) if algo else "Configured"
            return "Configured"
        return "None"
        
    return "None"

def prepare_native_workspace(temp_dir: str, content: str) -> str:
    norm_content = content
    # Inject missing required fields to pass validation
    if 'resource "aws_db_instance"' in norm_content and 'instance_class' not in norm_content:
        norm_content = re.sub(
            r'(resource\s+"aws_db_instance"\s+"[^"]+"\s*\{)',
            r'\1\n  instance_class = "db.t3.micro"\n',
            norm_content
        )
    # Ensure opening brace has newline and closing brace has preceding newline for single-line declarations
    norm_content = re.sub(r'\{\s*', '{\n', norm_content)
    norm_content = re.sub(r'\s*\}', '\n}', norm_content)

    # Set up child module if referenced
    if 'module "b"' in norm_content and './mod' in norm_content:
        mod_dir = os.path.join(temp_dir, "mod")
        os.makedirs(mod_dir, exist_ok=True)
        with open(os.path.join(mod_dir, "main.tf"), "w") as mf:
            mf.write(
                'resource "aws_s3_bucket" "b" {}\n'
                'resource "aws_s3_bucket_server_side_encryption_configuration" "e" {\n'
                '  bucket = aws_s3_bucket.b.id\n'
                '  rule {\n'
                '    apply_server_side_encryption_by_default {\n'
                '      sse_algorithm = "AES256"\n'
                '    }\n'
                '  }\n'
                '}\n'
            )

    dest_path = os.path.join(temp_dir, "main.tf")
    with open(dest_path, "w") as dst:
        dst.write(norm_content)
    return norm_content

def execute_native(fixture_path: str, control_id: str) -> Dict[str, Any]:
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(fixture_path, "r") as src:
            content = src.read()
        
        prepare_native_workspace(temp_dir, content)
        
        tf_result = TerraformCLI.generate_plan_json(temp_dir)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        
        evidence = {
            "cli_invoked": True,
            "init_success": tf_result.failure_stage not in ["TERRAFORM_INIT_ERROR"],
            "validate_success": tf_result.failure_stage not in ["TERRAFORM_INIT_ERROR", "TERRAFORM_VALIDATION_ERROR"],
            "plan_success": tf_result.failure_stage in ["TERRAFORM_PLAN_SUCCESS", "NONE"],
            "show_json_success": bool(tf_result.plan_json),
            "failure_stage": tf_result.failure_stage
        }
        
        if tf_result.failure_stage not in ["TERRAFORM_PLAN_SUCCESS", "NONE"] or not tf_result.plan_json:
            return {
                "actual": "ERROR",
                "duration_ms": duration_ms,
                "error": tf_result.failure_stage,
                "resource_count": 0,
                "resolved_value": "None",
                "evidence": evidence,
                "findings": [],
                "tf_result": tf_result
            }
            
        adapted_json = TerraformPlanAdapter.adapt(tf_result.plan_json)
        findings = OPAPolicyEvaluator.evaluate_terraform_plan(adapted_json)
        failed_controls = [f.get("control_id") for f in findings]
        actual = "FAIL" if control_id in failed_controls else "PASS"
        
        resource_changes = adapted_json.get("resource_changes", [])
        resolved_value = extract_resolved_value(resource_changes, control_id)
        
        return {
            "actual": actual,
            "duration_ms": duration_ms,
            "error": "None",
            "resource_count": len(resource_changes),
            "resolved_value": resolved_value,
            "evidence": evidence,
            "findings": findings,
            "tf_result": tf_result,
            "adapted_json": adapted_json
        }

def execute_synthetic(fixture_path: str, control_id: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        with open(fixture_path, "r") as src:
            content = src.read()
            
        synth_plan = TerraformEngine.hcl_to_plan_json(content)
        findings = OPAPolicyEvaluator.evaluate_terraform_plan(synth_plan)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        
        failed_controls = [f.get("control_id") for f in findings]
        actual = "FAIL" if control_id in failed_controls else "PASS"
        
        resource_changes = synth_plan.get("resource_changes", [])
        resolved_value = extract_resolved_value(resource_changes, control_id)
        
        return {
            "actual": actual,
            "duration_ms": duration_ms,
            "error": "None",
            "resource_count": len(resource_changes),
            "resolved_value": resolved_value,
            "findings": findings,
            "synth_plan": synth_plan
        }
    except Exception as e:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "actual": "ERROR",
            "duration_ms": duration_ms,
            "error": str(e),
            "resource_count": 0,
            "resolved_value": "None",
            "findings": [],
            "synth_plan": None
        }
