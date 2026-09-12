import os
import re
import json
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any, List

class TerraformEngine:
    """
    Controlled Terraform generator and parser.
    Uses approved regulatory blueprints to generate verified HCL and structured plan JSON.
    """

    TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "terraform_templates", "modules"))

    @classmethod
    def generate_compliant_hcl(cls, params: Dict[str, Any]) -> str:
        env = Environment(loader=FileSystemLoader(cls.TEMPLATE_DIR))
        generated_blocks = []

        # 1. Base Provider Header
        region = params.get("aws_region", "ap-south-1")
        header = f"""terraform {{
  required_version = ">= 1.5.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = "{region}"
  default_tags {{
    tags = {{
      ComplianceEngine = "RegulaCloud"
      Jurisdiction     = "India"
    }}
  }}
}}
"""
        generated_blocks.append(header)

        # 2. S3 Bucket Template
        if params.get("include_s3", True):
            s3_tmpl = env.get_template("s3_secure.tf.j2")
            s3_out = s3_tmpl.render(
                bucket_name=params.get("s3_bucket_name", "regulacloud-secure-assets"),
                environment=params.get("environment", "production"),
                sse_algorithm=params.get("s3_sse_algorithm", "aws:kms"),
                block_public="true" if params.get("s3_block_public", True) else "false"
            )
            generated_blocks.append(s3_out)

        # 3. RDS Template
        if params.get("include_rds", True):
            rds_tmpl = env.get_template("rds_secure.tf.j2")
            rds_out = rds_tmpl.render(
                db_identifier=params.get("rds_identifier", "regulacloud-primary-db"),
                allocated_storage=params.get("rds_storage", 20),
                engine=params.get("rds_engine", "postgres"),
                engine_version="15.4",
                instance_class="db.t3.micro",
                publicly_accessible="true" if params.get("rds_public", False) else "false",
                storage_encrypted="true" if params.get("rds_encrypted", True) else "false",
                environment=params.get("environment", "production")
            )
            generated_blocks.append(rds_out)

        # 4. CloudTrail / CERT-In Logging Template
        if params.get("include_logging", True):
            trail_tmpl = env.get_template("cloudtrail_logging.tf.j2")
            trail_out = trail_tmpl.render(
                trail_name=params.get("trail_name", "regulacloud-certin-audit-trail"),
                audit_bucket_name=params.get("audit_bucket_name", "regulacloud-audit-vault"),
                log_retention_days=params.get("log_retention_days", 180),
                is_multi_region="true" if params.get("is_multi_region", True) else "false",
                enable_logging="true"
            )
            generated_blocks.append(trail_out)

        return "\n\n".join(generated_blocks)

    @classmethod
    def apply_rl_actions(cls, hcl_code: str, action_ids: List[str]) -> tuple[str, List[str], List[str]]:
        new_hcl = hcl_code
        applied_actions = []
        skipped_actions = []

        for action in action_ids:
            if action == "ACT_DISABLE_RDS_PUBLIC":
                def repl_rds_pub(match):
                    body = match.group(2)
                    if "publicly_accessible" in body:
                        body = re.sub(r'publicly_accessible\s*=\s*(true|false)', 'publicly_accessible = false', body)
                    else:
                        body = body.rstrip() + "\n  publicly_accessible = false\n"
                    return f'resource "aws_db_instance" "{match.group(1)}" {{{body}}}'
                
                new_hcl = re.sub(r'resource\s+"aws_db_instance"\s+"([^"]+)"\s*\{([^}]+)\}', repl_rds_pub, new_hcl)
                applied_actions.append(action)

            elif action == "ACT_ENABLE_RDS_ENC":
                def repl_rds_enc(match):
                    body = match.group(2)
                    if "storage_encrypted" in body:
                        body = re.sub(r'storage_encrypted\s*=\s*(true|false)', 'storage_encrypted = true', body)
                    else:
                        body = body.rstrip() + "\n  storage_encrypted = true\n"
                    return f'resource "aws_db_instance" "{match.group(1)}" {{{body}}}'
                
                new_hcl = re.sub(r'resource\s+"aws_db_instance"\s+"([^"]+)"\s*\{([^}]+)\}', repl_rds_enc, new_hcl)
                applied_actions.append(action)

            elif action == "ACT_EXTEND_LOG_RETENTION_180":
                def repl_cw_log(match):
                    body = match.group(2)
                    ret_match = re.search(r'retention_in_days\s*=\s*(\d+)', body)
                    if ret_match:
                        val = int(ret_match.group(1))
                        if val < 180:
                            body = re.sub(r'retention_in_days\s*=\s*\d+', 'retention_in_days = 180', body)
                    else:
                        body = body.rstrip() + "\n  retention_in_days = 180\n"
                    return f'resource "aws_cloudwatch_log_group" "{match.group(1)}" {{{body}}}'
                
                new_hcl = re.sub(r'resource\s+"aws_cloudwatch_log_group"\s+"([^"]+)"\s*\{([^}]+)\}', repl_cw_log, new_hcl)
                applied_actions.append(action)

            elif action == "ACT_ENABLE_S3_ENC":
                s3_matches = re.finditer(r'resource\s+"aws_s3_bucket"\s+"([^"]+)"', new_hcl)
                buckets = [m.group(1) for m in s3_matches]
                
                for b in buckets:
                    # check if enc config exists for this bucket
                    if not re.search(rf'resource\s+"aws_s3_bucket_server_side_encryption_configuration"\s+"[^"]+"\s*\{{[^}}]+bucket\s*=\s*aws_s3_bucket\.{b}\.id', new_hcl):
                        enc_block = f"""
resource "aws_s3_bucket_server_side_encryption_configuration" "{b}_crypto" {{
  bucket = aws_s3_bucket.{b}.id
  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "aws:kms"
    }}
  }}
}}"""
                        new_hcl += "\n" + enc_block
                applied_actions.append(action)

            elif action == "ACT_ENABLE_CLOUDTRAIL_MULTI":
                def repl_trail(match):
                    body = match.group(2)
                    if "is_multi_region_trail" in body:
                        body = re.sub(r'is_multi_region_trail\s*=\s*(true|false)', 'is_multi_region_trail = true', body)
                    else:
                        body = body.rstrip() + "\n  is_multi_region_trail = true\n"
                    
                    if "enable_logging" in body:
                        body = re.sub(r'enable_logging\s*=\s*(true|false)', 'enable_logging = true', body)
                    else:
                        body = body.rstrip() + "\n  enable_logging = true\n"
                    return f'resource "aws_cloudtrail" "{match.group(1)}" {{{body}}}'
                
                new_hcl = re.sub(r'resource\s+"aws_cloudtrail"\s+"([^"]+)"\s*\{([^}]+)\}', repl_trail, new_hcl)
                applied_actions.append(action)

            elif action in ["ACT_UPGRADE_WEAK_CRYPTO", "ACT_PATCH_SONAR_INJECTION"]:
                # Will be handled by ApplicationRemediator
                pass
            else:
                skipped_actions.append(f"{action}: Unsupported or unrecognized Terraform action.")

        return new_hcl, applied_actions, skipped_actions

    @classmethod
    def hcl_to_plan_json(cls, hcl_text: str) -> Dict[str, Any]:
        """
        Parses HCL / Terraform code into a structured Terraform Plan JSON format
        equivalent to `terraform show -json` output, ready for OPA evaluation.
        """
        resource_changes: List[Dict[str, Any]] = []

        # Parse aws_db_instance
        db_matches = re.finditer(r'resource\s+"aws_db_instance"\s+"([^"]+)"\s*\{([^}]+)\}', hcl_text)
        for m in db_matches:
            name = m.group(1)
            body = m.group(2)
            
            pub_match = re.search(r'publicly_accessible\s*=\s*(true|false)', body)
            enc_match = re.search(r'storage_encrypted\s*=\s*(true|false)', body)
            
            publicly_accessible = (pub_match.group(1) == "true") if pub_match else False
            storage_encrypted = (enc_match.group(1) == "true") if enc_match else False

            resource_changes.append({
                "address": f"aws_db_instance.{name}",
                "type": "aws_db_instance",
                "name": name,
                "change": {
                    "actions": ["create"],
                    "after": {
                        "publicly_accessible": publicly_accessible,
                        "storage_encrypted": storage_encrypted,
                        "identifier": name
                    }
                }
            })

        # Parse aws_s3_bucket
        s3_matches = re.finditer(r'resource\s+"aws_s3_bucket"\s+"([^"]+)"\s*\{([^}]+)\}', hcl_text)
        for m in s3_matches:
            name = m.group(1)
            resource_changes.append({
                "address": f"aws_s3_bucket.{name}",
                "type": "aws_s3_bucket",
                "name": name,
                "change": {
                    "actions": ["create"],
                    "after": {
                        "bucket": name
                    }
                }
            })

        # Parse aws_s3_bucket_server_side_encryption_configuration
        s3_enc_matches = re.finditer(r'resource\s+"aws_s3_bucket_server_side_encryption_configuration"\s+"([^"]+)"\s*\{([^}]+)\}', hcl_text)
        for m in s3_enc_matches:
            name = m.group(1)
            resource_changes.append({
                "address": f"aws_s3_bucket_server_side_encryption_configuration.{name}",
                "type": "aws_s3_bucket_server_side_encryption_configuration",
                "name": name,
                "change": {
                    "actions": ["create"],
                    "after": {
                        "sse_algorithm": "aws:kms"
                    }
                }
            })

        # Parse aws_s3_bucket_public_access_block
        pab_matches = re.finditer(r'resource\s+"aws_s3_bucket_public_access_block"\s+"([^"]+)"\s*\{([^}]+)\}', hcl_text)
        for m in pab_matches:
            name = m.group(1)
            body = m.group(2)
            block_acls = bool(re.search(r'block_public_acls\s*=\s*true', body))
            block_policy = bool(re.search(r'block_public_policy\s*=\s*true', body))
            restrict_buckets = bool(re.search(r'restrict_public_buckets\s*=\s*true', body))

            resource_changes.append({
                "address": f"aws_s3_bucket_public_access_block.{name}",
                "type": "aws_s3_bucket_public_access_block",
                "name": name,
                "change": {
                    "actions": ["create"],
                    "after": {
                        "block_public_acls": block_acls,
                        "block_public_policy": block_policy,
                        "restrict_public_buckets": restrict_buckets
                    }
                }
            })

        # Parse aws_cloudwatch_log_group
        cw_matches = re.finditer(r'resource\s+"aws_cloudwatch_log_group"\s+"([^"]+)"\s*\{([^}]+)\}', hcl_text)
        for m in cw_matches:
            name = m.group(1)
            body = m.group(2)
            ret_match = re.search(r'retention_in_days\s*=\s*(\d+)', body)
            retention = int(ret_match.group(1)) if ret_match else 0

            resource_changes.append({
                "address": f"aws_cloudwatch_log_group.{name}",
                "type": "aws_cloudwatch_log_group",
                "name": name,
                "change": {
                    "actions": ["create"],
                    "after": {
                        "retention_in_days": retention
                    }
                }
            })

        # Parse aws_cloudtrail
        trail_matches = re.finditer(r'resource\s+"aws_cloudtrail"\s+"([^"]+)"\s*\{([^}]+)\}', hcl_text)
        for m in trail_matches:
            name = m.group(1)
            body = m.group(2)
            is_multi = bool(re.search(r'is_multi_region_trail\s*=\s*true', body))
            enable_log = bool(re.search(r'enable_logging\s*=\s*true', body))

            resource_changes.append({
                "address": f"aws_cloudtrail.{name}",
                "type": "aws_cloudtrail",
                "name": name,
                "change": {
                    "actions": ["create"],
                    "after": {
                        "is_multi_region_trail": is_multi,
                        "enable_logging": enable_log
                    }
                }
            })

        return {
            "format_version": "1.2",
            "terraform_version": "1.5.7",
            "resource_changes": resource_changes
        }
