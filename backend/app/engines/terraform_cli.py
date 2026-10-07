import os
import shutil
import tempfile
import subprocess
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TerraformCLIResult:
    def __init__(self, 
                 success: bool, 
                 validation_status: str, 
                 plan_json: Dict[str, Any], 
                 diagnostics: List[Dict[str, Any]], 
                 stdout: str, 
                 stderr: str, 
                 failure_stage: str):
        self.success = success
        self.validation_status = validation_status  # PASS, FAIL, ERROR
        self.plan_json = plan_json
        self.diagnostics = diagnostics
        self.stdout = stdout
        self.stderr = stderr
        self.failure_stage = failure_stage  # e.g., "FORMAT", "INIT", "VALIDATE", "PLAN", "SHOW", "NONE"

class TerraformCLI:
    """
    Real Terraform pipeline wrapper providing safe offline execution.
    Produces validated Plan JSON without provisioning cloud resources.
    """
    
    @staticmethod
    def _run_cmd(cmd: List[str], cwd: str, timeout_sec: int = 30) -> subprocess.CompletedProcess:
        # Sanitize environment to prevent secret leakage or credentials interference
        safe_env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin"),
            # Prevent accidental AWS credential resolution from local environment
            "AWS_ACCESS_KEY_ID": "mock_access_key",
            "AWS_SECRET_ACCESS_KEY": "mock_secret_key",
            "AWS_DEFAULT_REGION": "us-east-1",
            "TF_PLUGIN_CACHE_DIR": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".terraform_cache"))
        }
        os.makedirs(safe_env["TF_PLUGIN_CACHE_DIR"], exist_ok=True)
        
        try:
            return subprocess.run(
                cmd,
                cwd=cwd,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False
            )
        except FileNotFoundError:
            return subprocess.CompletedProcess(args=cmd, returncode=127, stdout="", stderr="Terraform executable not found. Please install Terraform.")

    @classmethod
    def generate_plan_json(cls, project_infrastructure_path: str) -> TerraformCLIResult:
        if not os.path.exists(project_infrastructure_path):
            return TerraformCLIResult(False, "ERROR", {}, [{"summary": "Infrastructure path missing"}], "", "", "INIT")

        with tempfile.TemporaryDirectory() as temp_dir:
            has_provider = False
            # 1. Safely copy ONLY .tf and .tfvars files to isolated workspace
            for root, _, files in os.walk(project_infrastructure_path):
                for f in files:
                    if f.endswith(".tf") or f.endswith(".tfvars"):
                        src = os.path.join(root, f)
                        rel_path = os.path.relpath(root, project_infrastructure_path)
                        dst_dir = os.path.join(temp_dir, rel_path) if rel_path != "." else temp_dir
                        os.makedirs(dst_dir, exist_ok=True)
                        
                        # Read content to check for provider and inject offline flags
                        with open(src, "r") as src_file:
                            content = src_file.read()
                        
                        if 'provider "aws"' in content or "provider 'aws'" in content:
                            has_provider = True
                            # Force offline provider behavior for security & speed
                            import re
                            content = re.sub(
                                r'(provider\s+"aws"\s*\{)',
                                r'\1\n  skip_credentials_validation = true\n  skip_requesting_account_id = true\n  skip_metadata_api_check = true\n  skip_region_validation = true\n  access_key = "mock"\n  secret_key = "mock"\n',
                                content
                            )
                            
                        dst = os.path.join(dst_dir, f)
                        with open(dst, "w") as dst_file:
                            dst_file.write(content)

            if not has_provider:
                with open(os.path.join(temp_dir, "zz_mock_provider.tf"), "w") as f:
                    f.write('''
provider "aws" {
  region                      = "us-east-1"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
  access_key                  = "mock"
  secret_key                  = "mock"
}
''')

            diagnostics = []
            
            try:
                # 2. terraform fmt -check -recursive
                fmt_res = cls._run_cmd(["terraform", "fmt", "-check", "-recursive"], cwd=temp_dir, timeout_sec=10)
                if fmt_res.returncode != 0:
                    diagnostics.append({"severity": "warning", "summary": "Code formatting does not comply with terraform fmt"})
                
                # 3. terraform init
                init_res = cls._run_cmd(["terraform", "init", "-input=false", "-no-color", "-backend=false", "-plugin-dir=/Users/adichaitanya/Downloads/REGULA-CLOUD-main/backend/app/engines/.terraform_providers"], cwd=temp_dir, timeout_sec=20)
                if init_res.returncode != 0:
                    diagnostics.append({"severity": "error", "summary": "Terraform init failed", "detail": init_res.stderr})
                    return TerraformCLIResult(False, "ERROR", {}, diagnostics, init_res.stdout, init_res.stderr, "TERRAFORM_INIT_ERROR")

                # 4. terraform validate -json
                val_res = cls._run_cmd(["terraform", "validate", "-json"], cwd=temp_dir, timeout_sec=15)
                if val_res.returncode != 0:
                    try:
                        val_data = json.loads(val_res.stdout)
                        diagnostics.extend(val_data.get("diagnostics", []))
                    except json.JSONDecodeError:
                        diagnostics.append({"severity": "error", "summary": "Validation failed unparseably", "detail": val_res.stderr})
                    return TerraformCLIResult(False, "ERROR", {}, diagnostics, val_res.stdout, val_res.stderr, "TERRAFORM_VALIDATION_ERROR")

                # 5. terraform plan
                plan_res = cls._run_cmd(["terraform", "plan", "-input=false", "-refresh=false", "-lock=false", "-no-color", "-out=tfplan"], cwd=temp_dir, timeout_sec=30)
                if plan_res.returncode != 0:
                    diagnostics.append({"severity": "error", "summary": "Terraform plan failed", "detail": plan_res.stderr})
                    return TerraformCLIResult(False, "ERROR", {}, diagnostics, plan_res.stdout, plan_res.stderr, "TERRAFORM_PLAN_ERROR")

                # 6. terraform show -json tfplan
                show_res = cls._run_cmd(["terraform", "show", "-json", "tfplan"], cwd=temp_dir, timeout_sec=15)
                if show_res.returncode != 0:
                    diagnostics.append({"severity": "error", "summary": "Terraform show failed", "detail": show_res.stderr})
                    return TerraformCLIResult(False, "ERROR", {}, diagnostics, show_res.stdout, show_res.stderr, "TERRAFORM_SHOW_ERROR")

                try:
                    plan_json = json.loads(show_res.stdout)
                except json.JSONDecodeError:
                    diagnostics.append({"severity": "error", "summary": "Could not parse plan JSON", "detail": show_res.stderr})
                    return TerraformCLIResult(False, "ERROR", {}, diagnostics, show_res.stdout, show_res.stderr, "TERRAFORM_SHOW_ERROR")

                return TerraformCLIResult(True, "PASS", plan_json, diagnostics, "", "", "TERRAFORM_PLAN_SUCCESS")

            except subprocess.TimeoutExpired as e:
                diagnostics.append({"severity": "error", "summary": "Terraform command timed out", "detail": str(e)})
                stage = "TERRAFORM_TIMEOUT"
                if "init" in e.cmd:
                    stage = "TERRAFORM_INIT_ERROR"
                elif "validate" in e.cmd:
                    stage = "TERRAFORM_VALIDATION_ERROR"
                elif "plan" in e.cmd:
                    stage = "TERRAFORM_PLAN_ERROR"
                elif "show" in e.cmd:
                    stage = "TERRAFORM_SHOW_ERROR"
                return TerraformCLIResult(False, "ERROR", {}, diagnostics, "", str(e), stage)

