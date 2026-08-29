package regulacloud.s3

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# Rule 1: S3 Bucket Encryption Enforcement (CTRL-AWS-S3-ENC)
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_s3_bucket"
    not has_valid_encryption(resource.address)
    msg := {
        "policy_id": "POL-DPDP-ENC-01",
        "control_id": "CTRL-AWS-S3-ENC",
        "resource": resource.address,
        "expected": "aws_s3_bucket_server_side_encryption_configuration with KMS or AES256",
        "actual": "No encryption configuration attached",
        "result": "FAIL",
        "explanation": "DPDP Act 2023 Sec 8(5) requires reasonable safeguards including storage encryption at rest."
    }
}

has_valid_encryption(bucket_address) if {
    some enc_resource in input.resource_changes
    enc_resource.type == "aws_s3_bucket_server_side_encryption_configuration"
}

# Rule 2: S3 Public Access Block Enforcement (CTRL-AWS-S3-NO-PUBLIC)
deny contains msg if {
    some resource in input.resource_changes
    resource.type == "aws_s3_bucket_public_access_block"
    val := resource.change.after
    val.block_public_acls == false
    msg := {
        "policy_id": "POL-DPDP-NET-01",
        "control_id": "CTRL-AWS-S3-NO-PUBLIC",
        "resource": resource.address,
        "expected": "block_public_acls=true",
        "actual": sprintf("block_public_acls=%v", [val.block_public_acls]),
        "result": "FAIL",
        "explanation": "Publicly accessible S3 buckets violate data isolation requirements under DPDP Act 2023."
    }
}
