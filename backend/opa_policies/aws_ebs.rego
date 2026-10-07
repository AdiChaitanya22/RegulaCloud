package regulacloud.ebs

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# CTRL-AWS-EBS-ENC
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_ebs_volume"
    val := resource.change.after
    
    not val.encrypted == true
    
    msg := {
        "policy_id": "POL-DPDP-ENC-01",
        "control_id": "CTRL-AWS-EBS-ENC",
        "resource": resource.address,
        "expected": "encrypted = true",
        "actual": sprintf("encrypted = %v", [val.encrypted]),
        "result": "FAIL",
        "explanation": "EBS volumes must be encrypted to satisfy DPDP storage encryption requirements."
    }
}
