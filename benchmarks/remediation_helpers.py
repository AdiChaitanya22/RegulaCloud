import os
import sys
import time
import shutil
import hashlib
import tempfile
import re
from typing import Dict, Any, Tuple, Optional, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app.engines.terraform_cli import TerraformCLI
from backend.app.engines.terraform_plan_adapter import TerraformPlanAdapter
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
from backend.app.engines.terraform_engine import TerraformEngine
from backend.app.engines.application_remediator import ApplicationRemediator
from backend.app.engines.sonarqube_client import SonarQubeClient

CONTROL_ACTION_MAP = {
    "CTRL-AWS-RDS-NO-PUBLIC": ("ACT_DISABLE_RDS_PUBLIC", "TerraformEngine"),
    "CTRL-AWS-RDS-STORAGE-ENC": ("ACT_ENABLE_RDS_ENC", "TerraformEngine"),
    "CTRL-AWS-S3-ENC": ("ACT_ENABLE_S3_ENC", "TerraformEngine"),
    "CTRL-AWS-LOG-180D": ("ACT_EXTEND_LOG_RETENTION_180", "TerraformEngine"),
    "CTRL-AWS-CLOUDTRAIL-MULTI": ("ACT_ENABLE_CLOUDTRAIL_MULTI", "TerraformEngine"),
    "CTRL-AWS-EC2-IMDSV2": ("ACT_ENFORCE_IMDSV2", "TerraformEngine"),
    "CTRL-AWS-EBS-ENC": ("ACT_ENABLE_EBS_ENC", "TerraformEngine"),
    "CTRL-AWS-KMS-ROTATION": ("ACT_ENABLE_KMS_ROTATION", "TerraformEngine"),
    "CTRL-APP-JAVA-SQLI": ("ACT_PATCH_SONAR_INJECTION", "ApplicationRemediator"),
    "CTRL-SONAR-INJECTION-FREE": ("ACT_PATCH_SONAR_INJECTION", "ApplicationRemediator"),
    "CTRL-APP-JAVA-CRYPTO": ("ACT_UPGRADE_WEAK_CRYPTO", "ApplicationRemediator"),
    "CTRL-SONAR-ZERO-CRITICAL": ("ACT_UPGRADE_WEAK_CRYPTO", "ApplicationRemediator"),
    "CTRL-AWS-SG-NO-OPEN-SSH": (None, "ManualSafety"),
    "CTRL-AWS-SG-NO-OPEN-RDP": (None, "ManualSafety"),
    "CTRL-AWS-IAM-NO-WILDCARD": (None, "ManualSafety")
}

def file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def prepare_remediation_native_workspace(temp_dir: str, content: str) -> str:
    """
    Normalizes fixture content for execution with Terraform CLI by ensuring
    provider required attributes are present and braces have newlines.
    """
    norm_content = content
    if 'resource "aws_db_instance"' in norm_content and 'instance_class' not in norm_content:
        norm_content = re.sub(
            r'(resource\s+"aws_db_instance"\s+"[^"]+"\s*\{)',
            r'\1\n  instance_class = "db.t3.micro"\n',
            norm_content
        )
    if 'resource "aws_instance"' in norm_content and 'ami' not in norm_content:
        norm_content = re.sub(
            r'(resource\s+"aws_instance"\s+"[^"]+"\s*\{)',
            r'\1\n  ami = "ami-12345678"\n  instance_type = "t3.micro"\n',
            norm_content
        )
    norm_content = re.sub(r'\{\s*', '{\n', norm_content)
    norm_content = re.sub(r'\s*\}', '\n}', norm_content)

    dest_path = os.path.join(temp_dir, "main.tf")
    with open(dest_path, "w") as dst:
        dst.write(norm_content)
    return norm_content

def evaluate_terraform_native(temp_dir: str, content: str, control_id: str) -> Tuple[str, bool, bool, List[Any]]:
    """
    Executes real Terraform CLI pipeline and OPA policy evaluation on temp_dir.
    Returns: (status, terraform_validation_success, native_plan_success, findings)
    """
    prepare_remediation_native_workspace(temp_dir, content)
    tf_result = TerraformCLI.generate_plan_json(temp_dir)
    
    val_success = (tf_result.validation_status == "PASS")
    plan_success = (tf_result.failure_stage in ["TERRAFORM_PLAN_SUCCESS", "NONE"] and bool(tf_result.plan_json))
    
    if not plan_success or not tf_result.plan_json:
        return "ERROR", val_success, False, []

    adapted = TerraformPlanAdapter.adapt(tf_result.plan_json)
    findings = OPAPolicyEvaluator.evaluate_terraform_plan(adapted)
    failed_controls = [f.get("control_id") for f in findings]
    actual = "FAIL" if control_id in failed_controls else "PASS"
    
    return actual, val_success, True, findings

def run_terraform_remediation_cycle(
    fixture_path: str,
    control_id: str,
    action_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs end-to-end real remediation evaluation on a temporary copy of a Terraform fixture:
    1. Initial detection
    2. Real mutation via TerraformEngine
    3. Post-remediation native validation & detection
    4. Idempotency verification (second mutation pass)
    5. Unrelated content preservation check
    """
    start_time = time.perf_counter()
    orig_sha_before = file_sha256(fixture_path)
    
    action_info = CONTROL_ACTION_MAP.get(control_id, (None, "TerraformEngine"))
    target_action = action_id if action_id is not None else action_info[0]

    with tempfile.TemporaryDirectory() as temp_dir:
        dest_main = os.path.join(temp_dir, "main.tf")
        with open(fixture_path, "r") as f:
            initial_content = f.read()

        before_hash = hashlib.sha256(initial_content.encode("utf-8")).hexdigest()

        # 1. Initial Native Detection
        initial_status, init_val_ok, init_plan_ok, init_findings = evaluate_terraform_native(
            temp_dir, initial_content, control_id
        )

        if target_action is None or action_info[1] == "ManualSafety":
            # Manual-only control safety path
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            assert file_sha256(fixture_path) == orig_sha_before, "Frozen fixture mutated!"
            return {
                "fixture_id": os.path.splitext(os.path.basename(fixture_path))[0],
                "control_id": control_id,
                "action_id": "None",
                "engine": "ManualSafety",
                "initial_status": initial_status,
                "source_changed": False,
                "changed_files": 0,
                "before_hash": before_hash,
                "after_hash": before_hash,
                "terraform_validation_success": init_val_ok,
                "native_plan_success": init_plan_ok,
                "final_status": initial_status,
                "idempotent": True,
                "second_run_changed": False,
                "unrelated_content_changed": False,
                "manual_only": True,
                "safe_skip": True,
                "duration_ms": duration_ms,
                "error": "None",
                "before_snippet": initial_content.strip(),
                "after_snippet": initial_content.strip()
            }

        # 2. Apply Real Terraform Remediation
        remediated_content, applied, skipped = TerraformEngine.apply_rl_actions(initial_content, [target_action])
        after_hash = hashlib.sha256(remediated_content.encode("utf-8")).hexdigest()
        source_changed = (before_hash != after_hash)

        # 3. Post-remediation Validation & Detection
        final_status, final_val_ok, final_plan_ok, final_findings = evaluate_terraform_native(
            temp_dir, remediated_content, control_id
        )

        # 4. Idempotency Verification
        second_before_hash = hashlib.sha256(remediated_content.encode("utf-8")).hexdigest()
        second_content, _, _ = TerraformEngine.apply_rl_actions(remediated_content, [target_action])
        second_after_hash = hashlib.sha256(second_content.encode("utf-8")).hexdigest()
        second_run_changed = (second_before_hash != second_after_hash)
        idempotent = not second_run_changed

        # 5. Unrelated content preservation check (tested with sentinel block)
        sentinel_block = '\n# SENTINEL UNRELATED RESOURCE\nresource "aws_s3_bucket" "audit_vault" { bucket = "immutable-vault" }\n'
        sentinel_test_hcl = initial_content + sentinel_block
        sentinel_remediated, _, _ = TerraformEngine.apply_rl_actions(sentinel_test_hcl, [target_action])
        unrelated_changed = ("immutable-vault" not in sentinel_remediated)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        assert file_sha256(fixture_path) == orig_sha_before, "Frozen fixture mutated!"

        return {
            "fixture_id": os.path.splitext(os.path.basename(fixture_path))[0],
            "control_id": control_id,
            "action_id": target_action,
            "engine": "TerraformEngine",
            "initial_status": initial_status,
            "source_changed": source_changed,
            "changed_files": 1 if source_changed else 0,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "terraform_validation_success": final_val_ok,
            "native_plan_success": final_plan_ok,
            "final_status": final_status,
            "idempotent": idempotent,
            "second_run_changed": second_run_changed,
            "unrelated_content_changed": unrelated_changed,
            "manual_only": False,
            "safe_skip": False,
            "duration_ms": duration_ms,
            "error": "None",
            "before_snippet": initial_content.strip(),
            "after_snippet": remediated_content.strip()
        }

def run_application_remediation_cycle(
    fixture_path: str,
    control_id: str,
    action_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs end-to-end real remediation evaluation on a temporary copy of a Java fixture:
    1. Initial static analysis scan
    2. Real mutation via ApplicationRemediator
    3. Post-remediation static analysis re-scan
    4. Idempotency verification (second mutation pass)
    5. Application comment/safety check
    """
    start_time = time.perf_counter()
    orig_sha_before = file_sha256(fixture_path)

    action_info = CONTROL_ACTION_MAP.get(control_id, (None, "ApplicationRemediator"))
    target_action = action_id if action_id is not None else action_info[0]

    with tempfile.TemporaryDirectory() as temp_dir:
        fname = os.path.basename(fixture_path)
        dest_file = os.path.join(temp_dir, fname)
        shutil.copyfile(fixture_path, dest_file)

        before_hash = file_sha256(dest_file)
        with open(dest_file, "r") as f:
            initial_content = f.read()

        scanner = SonarQubeClient()

        # 1. Initial Scan
        init_finds = scanner.scan_source_directory(temp_dir) or []
        target_cwe = "CWE-89" if "SQLI" in control_id else ("CWE-327" if "CRYPTO" in control_id else "")
        init_matching = [f for f in init_finds if target_cwe and f.get("cwe") == target_cwe]
        initial_status = "FAIL" if len(init_matching) > 0 else "PASS"

        # 2. Apply Application Remediation
        applied, skipped, changed_files = ApplicationRemediator.apply_source_actions(temp_dir, [target_action])
        after_hash = file_sha256(dest_file)
        source_changed = (before_hash != after_hash)
        
        with open(dest_file, "r") as f:
            remediated_content = f.read()

        # 3. Post-remediation Scan
        final_finds = scanner.scan_source_directory(temp_dir) or []
        final_matching = [f for f in final_finds if target_cwe and f.get("cwe") == target_cwe]
        final_status = "FAIL" if len(final_matching) > 0 else "PASS"

        # 4. Idempotency Verification
        second_before_hash = file_sha256(dest_file)
        app2, skip2, ch2 = ApplicationRemediator.apply_source_actions(temp_dir, [target_action])
        second_after_hash = file_sha256(dest_file)
        second_run_changed = (second_before_hash != second_after_hash)
        idempotent = not second_run_changed

        # 5. Comment safety check
        safe_skip = bool(len(skipped) > 0 and not source_changed)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        assert file_sha256(fixture_path) == orig_sha_before, "Frozen fixture mutated!"

        return {
            "fixture_id": os.path.splitext(fname)[0],
            "control_id": control_id,
            "action_id": target_action,
            "engine": "ApplicationRemediator",
            "initial_status": initial_status,
            "source_changed": source_changed,
            "changed_files": len(changed_files),
            "before_hash": before_hash,
            "after_hash": after_hash,
            "terraform_validation_success": True,
            "native_plan_success": True,
            "final_status": final_status,
            "idempotent": idempotent,
            "second_run_changed": second_run_changed,
            "unrelated_content_changed": False,
            "manual_only": False,
            "safe_skip": safe_skip,
            "duration_ms": duration_ms,
            "error": "None",
            "before_snippet": initial_content.strip(),
            "after_snippet": remediated_content.strip(),
            "initial_findings": init_matching,
            "final_findings": final_matching
        }
