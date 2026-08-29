package regulacloud.rds

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# Rule 1: Disallow Publicly Accessible RDS (CTRL-AWS-RDS-NO-PUBLIC)
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_db_instance"
    resource.change.after.publicly_accessible == true
    msg := {
        "policy_id": "POL-DPDP-NET-01",
        "control_id": "CTRL-AWS-RDS-NO-PUBLIC",
        "resource": resource.address,
        "expected": "publicly_accessible = false",
        "actual": "publicly_accessible = true",
        "result": "FAIL",
        "explanation": "Public database exposure violates DPDP Section 8(1) purpose limitation and isolation boundary requirements."
    }
}

# Rule 2: Enforce RDS Storage Encryption (CTRL-AWS-RDS-STORAGE-ENC)
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_db_instance"
    not resource.change.after.storage_encrypted == true
    msg := {
        "policy_id": "POL-DPDP-ENC-01",
        "control_id": "CTRL-AWS-RDS-STORAGE-ENC",
        "resource": resource.address,
        "expected": "storage_encrypted = true",
        "actual": sprintf("storage_encrypted = %v", [resource.change.after.storage_encrypted]),
        "result": "FAIL",
        "explanation": "DPDP Act Section 8(5) mandates encryption-at-rest for databases storing citizen personal records."
    }
}
