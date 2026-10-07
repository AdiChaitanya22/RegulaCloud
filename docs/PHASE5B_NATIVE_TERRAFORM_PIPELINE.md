# Phase 5B: Native Terraform Pipeline

## Overview
Phase 5B transitions RegulaCloud's compliance engine from a regex-based synthetic HCL parser to a fully native `terraform show -json` evaluation pipeline, ensuring that policies operate on exactly what Terraform will execute, fully resolving variables, locals, counts, and modules.

## Architecture Change
**BEFORE (Synthetic Mode):**
HCL Source -> Regex Parser -> Synthetic Plan JSON -> OPA Policies

**AFTER (Native Mode):**
HCL Source -> `terraform_cli` engine -> Native `terraform show -json` output -> `TerraformPlanAdapter` -> Canonical RegulaCloud JSON -> OPA Policies

## Execution Model
The `TerraformCLI` engine manages the entire lifecycle of the native plan:
1. Creates an isolated temporary workspace directory
2. Copies only `.tf` and `.tfvars` artifacts to the workspace
3. Injects offline provider credentials and overrides
4. Evaluates `terraform fmt`, `init`, `validate`, `plan`, and `show -json`
5. Discards the workspace
6. Computes `plan_hash` for cryptographic provenance tracking.

## Fail-Closed Compliance
If any stage of the CLI execution fails (e.g. invalid syntax, provider errors, initialization failures), the engine emits an explicit `TERRAFORM_VALIDATION_ERROR` or `TERRAFORM_PLAN_ERROR` and halts compliance evaluation, blocking deployment. It will not silently fall back to synthetic scanning.

## Offline Evaluation Performance
To ensure tests run fast and environments stay secure, we leverage `-plugin-dir` pointing to a local `.terraform_providers` cache and enforce `skip_credentials_validation` flags into an injected `zz_mock_provider.tf`. This avoids downloading massive binaries or hitting AWS STS via `GetCallerIdentity` during `terraform plan`.
