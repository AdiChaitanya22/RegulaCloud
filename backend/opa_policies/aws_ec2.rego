package regulacloud.ec2

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# CTRL-AWS-EC2-IMDSV2
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_instance"
    val := resource.change.after
    
    # Check if metadata_options exists and http_tokens == "required"
    not has_imds_v2(val)
    
    msg := {
        "policy_id": "POL-DPDP-SEC-01",
        "control_id": "CTRL-AWS-EC2-IMDSV2",
        "resource": resource.address,
        "expected": "metadata_options.http_tokens = 'required'",
        "actual": "Missing or optional IMDSv2",
        "result": "FAIL",
        "explanation": "IMDSv2 is required to prevent SSRF attacks against instance metadata."
    }
}

has_imds_v2(val) if {
    some opt in val.metadata_options
    opt.http_tokens == "required"
}
