package regulacloud.iam

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# CTRL-AWS-IAM-NO-WILDCARD
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_iam_policy"
    val := resource.change.after
    
    # Terraform encodes policy JSON as a string
    policy_doc := json.unmarshal(val.policy)
    
    some statement in policy_doc.Statement
    statement.Effect == "Allow"
    has_wildcard_action(statement)
    
    msg := {
        "policy_id": "POL-DPDP-IAM-01",
        "control_id": "CTRL-AWS-IAM-NO-WILDCARD",
        "resource": resource.address,
        "expected": "No Action = '*'",
        "actual": "Found wildcard action in Allow statement",
        "result": "FAIL",
        "explanation": "IAM policies must adhere to least privilege and avoid wildcard actions."
    }
}

has_wildcard_action(statement) if {
    statement.Action == "*"
}

has_wildcard_action(statement) if {
    is_array(statement.Action)
    some action in statement.Action
    action == "*"
}
