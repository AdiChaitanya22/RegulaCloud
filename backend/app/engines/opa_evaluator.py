import json
import subprocess
import shutil
import os
import tempfile
from typing import Dict, Any, List

class OPAPolicyEvaluator:
    """
    Evaluates Terraform plan JSON representation against OPA/Rego policies.
    Returns structured results: PASS / FAIL / UNKNOWN with exact violation details.
    """

    POLICIES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "opa_policies"))
    LOCAL_OPA_BIN = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "opa"))

    @classmethod
    def evaluate_terraform_plan(cls, tfplan_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        
        # Check if local standalone OPA binary or system OPA binary exists
        opa_bin = cls.LOCAL_OPA_BIN if os.path.isfile(cls.LOCAL_OPA_BIN) and os.access(cls.LOCAL_OPA_BIN, os.X_OK) else shutil.which("opa")
        
        if opa_bin and os.path.isdir(cls.POLICIES_DIR):
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
                    json.dump(tfplan_json, tmp)
                    tmp_path = tmp.name

                cmd = [
                    opa_bin, "eval",
                    "--data", cls.POLICIES_DIR,
                    "--input", tmp_path,
                    "data.regulacloud"
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

                if proc.returncode == 0:
                    eval_data = json.loads(proc.stdout)
                    result_rows = eval_data.get("result", [{}])[0].get("expressions", [{}])[0].get("value", {})
                    for pkg_name, pkg_rules in result_rows.items():
                        if isinstance(pkg_rules, dict) and "deny" in pkg_rules:
                            for violation in pkg_rules["deny"]:
                                findings.append(violation)
                    return findings
                else:
                    print(f"[WARN] OPA CLI returned non-zero code ({proc.returncode}): {proc.stderr}")
            except Exception as e:
                print(f"[WARN] OPA CLI execution error: {e}")

        # Native Evaluator Fallback
        resource_changes = tfplan_json.get("resource_changes", [])
        for r in resource_changes:
            rtype = r.get("type")
            address = r.get("address", "")
            after = (r.get("change") or {}).get("after") or {}

            if rtype == "aws_db_instance":
                if after.get("publicly_accessible") is True:
                    findings.append({
                        "policy_id": "POL-DPDP-NET-01",
                        "control_id": "CTRL-AWS-RDS-NO-PUBLIC",
                        "resource": address,
                        "expected": "publicly_accessible = false",
                        "actual": "publicly_accessible = true",
                        "result": "FAIL",
                        "explanation": "Public database exposure violates DPDP Section 8(1) purpose limitation and isolation boundary requirements."
                    })
                if not after.get("storage_encrypted") is True:
                    findings.append({
                        "policy_id": "POL-DPDP-ENC-01",
                        "control_id": "CTRL-AWS-RDS-STORAGE-ENC",
                        "resource": address,
                        "expected": "storage_encrypted = true",
                        "actual": f"storage_encrypted = {after.get('storage_encrypted')}",
                        "result": "FAIL",
                        "explanation": "DPDP Act Section 8(5) mandates encryption-at-rest for databases storing citizen personal records."
                    })

            if rtype == "aws_s3_bucket":
                has_enc = any(
                    x.get("type") == "aws_s3_bucket_server_side_encryption_configuration"
                    for x in resource_changes
                ) or after.get("server_side_encryption_configuration")
                if not has_enc:
                    findings.append({
                        "policy_id": "POL-DPDP-ENC-01",
                        "control_id": "CTRL-AWS-S3-ENC",
                        "resource": address,
                        "expected": "aws_s3_bucket_server_side_encryption_configuration with KMS or AES256",
                        "actual": "No encryption configuration attached",
                        "result": "FAIL",
                        "explanation": "DPDP Act 2023 Sec 8(5) requires reasonable safeguards including storage encryption at rest."
                    })

            if rtype == "aws_s3_bucket_public_access_block":
                if after.get("block_public_acls") is False or after.get("block_public_policy") is False or after.get("restrict_public_buckets") is False:
                    findings.append({
                        "policy_id": "POL-DPDP-NET-01",
                        "control_id": "CTRL-AWS-S3-NO-PUBLIC",
                        "resource": address,
                        "expected": "block_public_acls=true",
                        "actual": f"block_public_acls={after.get('block_public_acls')}",
                        "result": "FAIL",
                        "explanation": "Publicly accessible S3 buckets violate data isolation requirements under DPDP Act 2023."
                    })

            if rtype == "aws_cloudwatch_log_group":
                retention = after.get("retention_in_days", 0)
                if retention < 180:
                    findings.append({
                        "policy_id": "POL-CERTIN-LOG-180",
                        "control_id": "CTRL-AWS-LOG-180D",
                        "resource": address,
                        "expected": "retention_in_days >= 180",
                        "actual": f"retention_in_days = {retention}",
                        "result": "FAIL",
                        "explanation": "CERT-In 2022 Directions Sec 2(v) mandates rolling log retention of at least 180 days."
                    })

            if rtype == "aws_cloudtrail":
                is_multi = after.get("is_multi_region_trail") is True
                is_enabled = after.get("enable_logging") is True
                if not (is_multi and is_enabled):
                    findings.append({
                        "policy_id": "POL-CERTIN-CLOUDTRAIL",
                        "control_id": "CTRL-AWS-CLOUDTRAIL-MULTI",
                        "resource": address,
                        "expected": "is_multi_region_trail = true",
                        "actual": f"is_multi_region_trail = {after.get('is_multi_region_trail')}",
                        "result": "FAIL",
                        "explanation": "CERT-In 2022 Directions Sec 2(ii) requires multi-region audit trails for 6-hour incident disclosure readiness."
                    })

        return findings
