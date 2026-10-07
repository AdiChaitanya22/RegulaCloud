package regulacloud.kms

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# CTRL-AWS-KMS-ROTATION
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_kms_key"
    val := resource.change.after
    
    not val.enable_key_rotation == true
    
    msg := {
        "policy_id": "POL-CERTIN-CRYPTO-01",
        "control_id": "CTRL-AWS-KMS-ROTATION",
        "resource": resource.address,
        "expected": "enable_key_rotation = true",
        "actual": sprintf("enable_key_rotation = %v", [val.enable_key_rotation]),
        "result": "FAIL",
        "explanation": "KMS keys must have automatic key rotation enabled."
    }
}
