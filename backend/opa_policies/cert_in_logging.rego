package regulacloud.logging

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# Rule 1: CERT-In Mandatory 180-day log retention (CTRL-AWS-LOG-180D)
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_cloudwatch_log_group"
    retention := object.get(resource.change.after, "retention_in_days", 0)
    retention < 180
    msg := {
        "policy_id": "POL-CERTIN-LOG-180",
        "control_id": "CTRL-AWS-LOG-180D",
        "resource": resource.address,
        "expected": "retention_in_days >= 180",
        "actual": sprintf("retention_in_days = %v", [retention]),
        "result": "FAIL",
        "explanation": "CERT-In 2022 Directions Sec 2(v) mandates rolling log retention of at least 180 days."
    }
}

# Rule 2: Multi-Region CloudTrail Trail (CTRL-AWS-CLOUDTRAIL-MULTI)
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_cloudtrail"
    not resource.change.after.is_multi_region_trail == true
    msg := {
        "policy_id": "POL-CERTIN-CLOUDTRAIL",
        "control_id": "CTRL-AWS-CLOUDTRAIL-MULTI",
        "resource": resource.address,
        "expected": "is_multi_region_trail = true",
        "actual": sprintf("is_multi_region_trail = %v", [resource.change.after.is_multi_region_trail]),
        "result": "FAIL",
        "explanation": "CERT-In 2022 Directions Sec 2(ii) requires multi-region audit trails for 6-hour incident disclosure readiness."
    }
}
