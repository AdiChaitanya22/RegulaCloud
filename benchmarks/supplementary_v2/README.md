# RegulaCloud Supplementary V2 Benchmark Corpus

> **STATUS**: SUPPLEMENTARY EXPERIMENTAL BENCHMARK CORPUS (V2)  
> **IMMUTABILITY NOTICE**: This supplementary corpus is independent of the Primary V1 Frozen Baseline.  
> Primary V1 (`1792700005-OFFICIAL-REAL`, Harness commit `8d970b05`, Manifest `fccdecf5`, RL `29b1eb07`) remains fully immutable.

---

## 1. Motivation and Purpose

The Phase 6 primary evaluation revealed several empirical limitations and threats to internal validity:
1. **Provider-Invalid Fixtures**: 12 Terraform fixtures failed native planning due to missing provider schema attributes (e.g. S3 PAB `bucket` reference, CloudTrail `s3_bucket_name`, EC2 `ami`/`instance_type`, EBS `availability_zone`).
2. **Confounded Classification Metrics**: Fixtures failing schema planning introduced uncalibrated non-decisive results into classification evaluation.
3. **Single-Violation RL Corpus**: The V1 RL state space tested only 1-hot states, leaving sequential policy performance unvalidated on multi-violation topologies.
4. **Remediation Validation Quality**: Application fixtures in V1 lacked standalone compiler validity and clear separation between classification ground truth and remediator safe-skip behavior.

Supplementary V2 constructs an uncompromised, pre-validated corpus to address each threat while preserving V1 as the frozen historical baseline.

---

## 2. Corpus Structure

```
benchmarks/supplementary_v2/
├── README.md                      # Supplementary V2 methodology documentation
├── manifest_v2.json               # 40-fixture ground-truth manifest
├── terraform/
│   ├── compliant/                 # 11 provider-valid compliant fixtures (PASS)
│   ├── noncompliant/              # 11 provider-valid non-compliant fixtures (FAIL)
│   └── semantic/                  # 10 advanced HCL feature fixtures
├── application/
│   ├── compliant/                 # 2 javac-compilable compliant Java classes (PASS)
│   ├── vulnerable/                # 3 javac-compilable vulnerable Java classes (FAIL)
│   └── edge/                      # 3 javac-compilable edge cases (comment, safe-skip)
├── rl/
│   └── states_v2.json             # 30 unique multi-violation RL states
└── tests/
    ├── test_supplementary_integrity.py  # Corpus structural and execution integrity tests
    └── test_supplementary_rl.py         # RL state space validation tests
```

---

## 3. Fixture Inventory

### 3.1 Terraform Classification Corpus (22 Paired Fixtures)
Tests 11 core AWS controls across balanced PASS/FAIL pairs:
- `CTRL-AWS-RDS-NO-PUBLIC` (`aws_db_instance`)
- `CTRL-AWS-RDS-STORAGE-ENC` (`aws_db_instance`)
- `CTRL-AWS-S3-ENC` (`aws_s3_bucket`)
- `CTRL-AWS-S3-NO-PUBLIC` (`aws_s3_bucket_public_access_block`)
- `CTRL-AWS-LOG-180D` (`aws_cloudwatch_log_group`)
- `CTRL-AWS-CLOUDTRAIL-MULTI` (`aws_cloudtrail`)
- `CTRL-AWS-EC2-IMDSV2` (`aws_instance`)
- `CTRL-AWS-EBS-ENC` (`aws_ebs_volume`)
- `CTRL-AWS-KMS-ROTATION` (`aws_kms_key`)
- `CTRL-AWS-SG-NO-OPEN-SSH` (`aws_security_group`)
- `CTRL-AWS-SG-NO-OPEN-RDP` (`aws_security_group`)

Every fixture initializes offline, validates, plans, and shows clean plan JSON without provider errors. Supporting resources (e.g. S3 bucket for CloudTrail) are configured compliantly to prevent cross-control violation leakage.

### 3.2 Terraform Semantic Corpus (10 Fixtures)
Tests HCL2 semantic constructs with known frozen expectations:
- `literal PASS`: EBS encryption (1 instance, `encrypted = true`)
- `literal FAIL`: EBS encryption (1 instance, `encrypted = false`)
- `variable`: RDS public ingress via variable default (1 instance, `publicly_accessible = false`)
- `local`: RDS storage encryption via local variable (1 instance, `storage_encrypted = true`)
- `module`: Self-contained child module declaring encrypted S3 bucket (2 instances, `sse_algorithm = 'AES256'`)
- `conditional`: CloudWatch log retention via ternary conditional (1 instance, `retention_in_days = 180`)
- `count`: CloudWatch log group with `count = 2` (2 instances, `retention_in_days = 180`)
- `for_each`: EBS volume with `for_each = toset([...])` (3 instances, `encrypted = true`)
- `resource_reference`: CloudTrail referencing supporting S3 bucket ID (3 instances, `is_multi_region_trail = true`)
- `nested_block`: EC2 instance with nested `metadata_options` (1 instance, `http_tokens = 'required'`)

### 3.3 Application Security Corpus (8 Java Fixtures)
All fixtures compile cleanly with `javac` in isolation:
- `CWE-89 (SQL Injection)`:
  - `vulnerable-sqli-simple`: Unsanitized concatenation (FAIL, AUTO_REMEDIATE)
  - `compliant-sqli-param`: PreparedStatement (PASS, NOT_APPLICABLE)
  - `edge-sqli-comment`: Commented concatenation (PASS, regex false-positive robustness test)
  - `edge-sqli-unsupported`: Multi-concatenation query (FAIL, SAFE_SKIP)
- `CWE-327 (Broken Crypto)`:
  - `vulnerable-crypto-des`: DES cipher in ECB mode (FAIL, AUTO_REMEDIATE)
  - `compliant-crypto-aes`: AES-256-GCM authenticated cipher (PASS, NOT_APPLICABLE)
  - `vulnerable-crypto-3des`: Triple DES / DESede cipher (FAIL, SAFE_SKIP)
  - `edge-crypto-comment`: Security commentary mentioning DES without triggering scanner (PASS, NOT_APPLICABLE)

### 3.4 Multi-Violation RL State Space (30 States)
30 unique binary tuples over the 11 production actions (indices 0..10):
- **5 single-violation states** (1 active action)
- **10 dual-violation states** (2 active actions)
- **10 multi-violation states** (3–5 active actions)
- **5 dense-violation states** (6–9 active actions)
- 100% action coverage (all 11 production actions represented across the corpus)
