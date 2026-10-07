# Native Terraform Security Model

## TOCTOU Defenses
The RegulaCloud architecture explicitly protects against Time-of-Check to Time-of-Use (TOCTOU) attacks by computing hashes of all execution artifacts at evaluation time:
- `infrastructure_hash`: Hash of all HCL source code
- `application_source_hash`: Hash of the application codebase
- `plan_hash`: Hash of the native Terraform JSON plan produced by `terraform_cli`.

During actual deployment, these hashes are recomputed and cross-checked against the `EvaluationRun` evidence payload. If any hash mismatches, or if the `plan_hash` is missing from a `TERRAFORM_NATIVE_PLAN` evaluation, the deployment is blocked unconditionally. No administrator override is permitted.

## Subprocess Sanitization
`terraform_cli.py` restricts Terraform execution strictly:
- Uses parameter arrays instead of `shell=True` to prevent command injection.
- Forces `-backend=false` and `-refresh=false` to avoid network connections.
- Mocks environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) and explicitly overrides any actual AWS configurations.
- Operates entirely out of isolated, temporary workspace directories, copying only `.tf` and `.tfvars` files over to avoid accidental execution or exposure of malicious scripts in the workspace.
- Enforces strict process timeouts for each command stage (e.g. `init`, `validate`, `plan`) to mitigate resource-exhaustion DOS attacks.

## Provider Authentication Protection
Because `terraform plan` attempts to authenticate via AWS STS for validation even with `refresh=false`, we programmatically scan for existing `provider "aws"` blocks and inject offline directives (`skip_credentials_validation = true`, etc.). If none exist, a global `zz_mock_provider.tf` is injected into the temporary directory. The provider engine leverages a local cache (`-plugin-dir`) to prevent reaching out to HashiCorp's registry.
