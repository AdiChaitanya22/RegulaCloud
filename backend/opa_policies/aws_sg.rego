package regulacloud.sg

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# CTRL-AWS-SG-NO-OPEN-SSH
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_security_group"
    val := resource.change.after
    
    some ingress in val.ingress
    ingress.from_port <= 22
    ingress.to_port >= 22
    has_open_cidr(ingress)
    
    msg := {
        "policy_id": "POL-DPDP-NET-01",
        "control_id": "CTRL-AWS-SG-NO-OPEN-SSH",
        "resource": resource.address,
        "expected": "No 0.0.0.0/0 on port 22",
        "actual": "Found open SSH ingress",
        "result": "FAIL",
        "explanation": "Security groups must not allow unrestricted SSH access from the internet."
    }
}

# CTRL-AWS-SG-NO-OPEN-RDP
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_security_group"
    val := resource.change.after
    
    some ingress in val.ingress
    ingress.from_port <= 3389
    ingress.to_port >= 3389
    has_open_cidr(ingress)
    
    msg := {
        "policy_id": "POL-DPDP-NET-01",
        "control_id": "CTRL-AWS-SG-NO-OPEN-RDP",
        "resource": resource.address,
        "expected": "No 0.0.0.0/0 on port 3389",
        "actual": "Found open RDP ingress",
        "result": "FAIL",
        "explanation": "Security groups must not allow unrestricted RDP access from the internet."
    }
}

has_open_cidr(ingress) if {
    some cidr in ingress.cidr_blocks
    cidr == "0.0.0.0/0"
}

has_open_cidr(ingress) if {
    some cidr in ingress.ipv6_cidr_blocks
    cidr == "::/0"
}
