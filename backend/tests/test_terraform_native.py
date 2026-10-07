import pytest
import os
import json
from backend.app.engines.terraform_cli import TerraformCLI, TerraformCLIResult

def test_terraform_cli_availability():
    import subprocess
    res = subprocess.run(["terraform", "version"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Terraform" in res.stdout

def test_terraform_cli_variables(tmp_path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
    variable "public_db" {
      type    = bool
      default = true
    }

    resource "aws_db_instance" "db" {
      publicly_accessible = var.public_db
      storage_encrypted   = false
      instance_class      = "db.t3.micro"
    }
    """)
    
    res = TerraformCLI.generate_plan_json(str(tmp_path))
    assert res.success is True
    assert res.validation_status == "PASS"
    
    # Verify variable was resolved
    changes = res.plan_json.get("resource_changes", [])
    assert len(changes) == 1
    assert changes[0]["change"]["after"]["publicly_accessible"] is True

def test_terraform_cli_locals(tmp_path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
    locals {
      log_retention = 30
    }

    resource "aws_cloudwatch_log_group" "logs" {
      retention_in_days = local.log_retention
    }
    """)
    
    res = TerraformCLI.generate_plan_json(str(tmp_path))
    assert res.success is True
    
    changes = res.plan_json.get("resource_changes", [])
    assert len(changes) == 1
    assert changes[0]["change"]["after"]["retention_in_days"] == 30

def test_terraform_cli_count(tmp_path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
    resource "aws_s3_bucket" "buckets" {
      count = 2
      bucket = "test-bucket-${count.index}"
    }
    """)
    
    res = TerraformCLI.generate_plan_json(str(tmp_path))
    assert res.success is True
    
    changes = res.plan_json.get("resource_changes", [])
    assert len(changes) == 2
    assert changes[0]["change"]["after"]["bucket"] == "test-bucket-0"
    assert changes[1]["change"]["after"]["bucket"] == "test-bucket-1"

def test_terraform_cli_local_module(tmp_path):
    main_tf = tmp_path / "main.tf"
    main_tf.write_text("""
    module "db" {
      source = "./modules/database"
    }
    """)
    
    mod_dir = tmp_path / "modules" / "database"
    mod_dir.mkdir(parents=True)
    mod_tf = mod_dir / "main.tf"
    mod_tf.write_text("""
    resource "aws_db_instance" "db" {
      instance_class = "db.t3.micro"
      publicly_accessible = false
    }
    """)
    
    res = TerraformCLI.generate_plan_json(str(tmp_path))
    assert res.success is True
    
    changes = res.plan_json.get("resource_changes", [])
    assert len(changes) == 1
    assert changes[0]["type"] == "aws_db_instance"

def test_terraform_cli_invalid_hcl(tmp_path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
    resource "aws_db_instance" "db" {
      publicly_accessible = 
    }
    """)
    
    res = TerraformCLI.generate_plan_json(str(tmp_path))
    assert res.success is False
    assert res.validation_status == "ERROR"
    assert "VALIDATION" in res.failure_stage or "ERROR" in res.failure_stage

def test_terraform_cli_opa_rds_public(tmp_path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
    resource "aws_db_instance" "db" {
      publicly_accessible = true
      storage_encrypted   = true
      instance_class      = "db.t3.micro"
    }
    """)
    
    res = TerraformCLI.generate_plan_json(str(tmp_path))
    assert res.success is True
    
    from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
    violations = OPAPolicyEvaluator.evaluate_terraform_plan(res.plan_json)
    assert any(v["control_id"] == "CTRL-AWS-RDS-NO-PUBLIC" for v in violations)

def test_terraform_cli_opa_s3_encryption(tmp_path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
    resource "aws_s3_bucket" "bucket" {
      bucket = "unencrypted-bucket"
    }
    """)
    
    res = TerraformCLI.generate_plan_json(str(tmp_path))
    assert res.success is True
    
    from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
    violations = OPAPolicyEvaluator.evaluate_terraform_plan(res.plan_json)
    assert any(v["control_id"] == "CTRL-AWS-S3-ENC" for v in violations)

def test_terraform_cli_cloudwatch_retention(tmp_path):
    tf_file = tmp_path / "main.tf"
    tf_file.write_text("""
    resource "aws_cloudwatch_log_group" "logs" {
      retention_in_days = 14
    }
    """)
    
    res = TerraformCLI.generate_plan_json(str(tmp_path))
    from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
    violations = OPAPolicyEvaluator.evaluate_terraform_plan(res.plan_json)
    assert any(v["control_id"] == "CTRL-AWS-LOG-180D" for v in violations)

