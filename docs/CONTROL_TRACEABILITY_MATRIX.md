# Control Traceability Matrix

## Traceability Matrix

| Regulation | Requirement | Technical Control | Evidence Source | Detection Rule | RL Action | Remediation Engine | Re-evaluation |
|------------|-------------|-------------------|-----------------|----------------|-----------|--------------------|---------------|
| DPDP Act 2023 | SEC8(1) Purpose Limitation | `CTRL-AWS-RDS-NO-PUBLIC` | Terraform Plan | OPA Fallback (Native Python) / Rego | `ACT_DISABLE_RDS_PUBLIC` | `TerraformEngine.apply_rl_actions` | Supported via `evaluate_compliance` |
| DPDP Act 2023 | SEC8(5) Encryption | `CTRL-AWS-RDS-STORAGE-ENC` | Terraform Plan | OPA Fallback (Native Python) / Rego | `ACT_ENABLE_RDS_ENC` | `TerraformEngine.apply_rl_actions` | Supported |
| DPDP Act 2023 | SEC8(5) Encryption | `CTRL-AWS-S3-ENC` | Terraform Plan | OPA Fallback (Native Python) / Rego | `ACT_ENABLE_S3_ENC` | `TerraformEngine.apply_rl_actions` | Supported |
| DPDP Act 2023 | SEC8(1) Data Isolation | `CTRL-AWS-S3-NO-PUBLIC` | Terraform Plan | OPA Fallback (Native Python) / Rego | `ACT_BLOCK_S3_PUBLIC` | **NONE** (Action exists, but `apply_rl_actions` missing logic!) | N/A |
| CERT-In 2022 | SEC2(v) Log Retention | `CTRL-AWS-LOG-180D` | Terraform Plan | OPA Fallback (Native Python) / Rego | `ACT_EXTEND_LOG_RETENTION_180` | `TerraformEngine.apply_rl_actions` | Supported |
| CERT-In 2022 | SEC2(ii) Audit Trails | `CTRL-AWS-CLOUDTRAIL-MULTI` | Terraform Plan | OPA Fallback (Native Python) / Rego | `ACT_ENABLE_CLOUDTRAIL_MULTI` | `TerraformEngine.apply_rl_actions` | Supported |
| General Security | Secure App Code | `CTRL-SONAR-INJECTION-FREE` | SonarQube / Source | Local Regex / SonarQube API (`CWE-89`) | `ACT_PATCH_SONAR_INJECTION` | `ApplicationRemediator.apply_source_actions` | Supported |
| General Security | Zero Critical Flaws | `CTRL-SONAR-ZERO-CRITICAL` | SonarQube / Source | Local Regex / SonarQube API (`CWE-327`) | `ACT_UPGRADE_WEAK_CRYPTO` | `ApplicationRemediator.apply_source_actions` | Supported |

## Gap Identification

1. **Controls that can be detected but not remediated:**
   - `CTRL-AWS-S3-NO-PUBLIC` (OPA can detect it, `ACT_BLOCK_S3_PUBLIC` is defined in RL Engine, but `TerraformEngine.apply_rl_actions` does not implement logic to actually patch it).

2. **Remediation actions with no active control:**
   - N/A (All 8 actions map to controls, though some lack implementation).

3. **Controls with no evidence source:**
   - Any technical control in the database that is not one of the 6 hardcoded AWS resources or 2 SonarQube CWEs.

4. **Duplicate controls:**
   - None found in hardcoded lists.

5. **Dead rules:**
   - Rego policies might be dead if `opa` binary is missing (System falls back to native Python rules).
   - Any Rego rule targeting non-supported AWS resources will never trigger because `hcl_to_plan_json` won't parse them.

6. **Unreachable remediation actions:**
   - `ACT_BLOCK_S3_PUBLIC` is unreachable/unsupported in the `TerraformEngine` patching function, causing it to be logged as a "skipped action".
