# Phase 5C: Native Policy Coverage Gaps

## Current State Matrix
| AWS Resource | Technical Control | Status | Auto-Remediation |
| --- | --- | --- | --- |
| `aws_db_instance` | No Public Access | ✅ Active | ❌ Detection Only |
| `aws_db_instance` | Storage Encryption | ✅ Active | ✅ Supported |
| `aws_s3_bucket` | Public Access Block | ✅ Active | ✅ Supported |
| `aws_s3_bucket` | Server-Side Encryption | ✅ Active | ✅ Supported |
| `aws_cloudwatch_log_group` | 180-day Retention | ✅ Active | ✅ Supported |
| `aws_cloudtrail` | Multi-Region enabled | ✅ Active | ✅ Supported |

Total Current Controls: **6**

## Recommended Phase 5C Policy Expansion
To systematically expand the technical boundary while keeping implementation realistic, I recommend implementing exactly 6 new controls. 

| Recommended Control | Resource | Detection / Remediation | Rationale |
| --- | --- | --- | --- |
| **Enforce IMDSv2** | `aws_instance` | ✅ Auto-Remediate Safe (`http_tokens = "required"`) | High security value (SSRF protection), zero ambiguity. |
| **EBS Encryption** | `aws_ebs_volume` | ✅ Auto-Remediate Safe (`encrypted = true`) | Direct regulatory requirement (Sec 8.5 DPDP). |
| **KMS Key Rotation** | `aws_kms_key` | ✅ Auto-Remediate Safe (`enable_key_rotation = true`) | Cryptographic lifecycle requirement. |
| **No Open SSH** | `aws_security_group` | ❌ Detection Only | Highly dangerous if misconfigured, but cannot be safely auto-remediated as the intended administrative CIDR is unknown. |
| **No Open RDP** | `aws_security_group` | ❌ Detection Only | Similar to SSH, detect only. |
| **IAM Wildcard Disallow** | `aws_iam_policy` | ❌ Detection Only | Hard to algorithmically determine least-privilege intent. Detect `Action = "*"` and fail. |

## Remediation Philosophy
Controls should only be hooked into the RL Remediation Engine if they are **deterministically safe** to apply blindly. Setting a boolean toggle for encryption (`encrypted = true`) is computationally safe. Modifying networking ingress rules or IAM policies blindly is extremely unsafe and must remain Detection-Only.
