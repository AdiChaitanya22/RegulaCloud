# Terraform Support Matrix

## Parser Engine Analysis
The current `TerraformEngine` relies exclusively on string `re.finditer` and `re.sub`.
It **does not** invoke the Terraform CLI (`terraform init`, `terraform plan`, or `terraform show -json`).
Instead, it synthesizes a mock Plan JSON representation by extracting explicit regex matches.

## Support Matrix

| Terraform Feature | Supported | Partial | Unsupported | Evidence |
|-------------------|-----------|---------|-------------|----------|
| **Standard Resources** | | x | | Only 6 specific AWS resources are parsed using hardcoded Regex in `hcl_to_plan_json`. |
| **Variables (`var.X`)** | | | x | Regex expects hardcoded boolean/string values (e.g., `publicly_accessible = true`). Variable interpolation fails. |
| **Locals (`local.X`)** | | | x | No AST parser exists to evaluate locals. |
| **Data Sources (`data.X`)** | | | x | Regex only matches `resource "aws_db_instance"` etc., entirely ignoring data blocks. |
| **Outputs** | | | x | Ignored by parser. |
| **Modules** | | | x | No support for `module {}` blocks or traversing module directories. |
| **Count / For_Each** | | | x | Metamodels like `count` and `for_each` are not evaluated, causing inaccurate JSON synthesis. |
| **Dynamic Blocks** | | | x | Block generation is completely static based on simple regex matching. |
| **Expressions & Conditionals** | | | x | Expressions like `var.env == "prod" ? true : false` break the `(true|false)` Regex match groups. |
| **Interpolation** | | | x | `${...}` syntax is interpreted literally or breaks regex bounds. |
| **Resource References** | | x | | Replaces references like `aws_s3_bucket.X.id` statically in remediation, but does not construct a dependency graph. |
| **Provider Aliases** | | | x | No provider parsing logic exists. |
| **Multiple .tf Files** | | x | | Supported via simplistic string concatenation in `projects.py` before parsing. |
| **Tfvars files** | | | x | Variable inputs are not accepted or merged. |
| **Backend blocks** | | | x | Ignored. |

## Supported AWS Resources (Hardcoded)
- `aws_db_instance`
- `aws_s3_bucket`
- `aws_s3_bucket_server_side_encryption_configuration`
- `aws_s3_bucket_public_access_block`
- `aws_cloudwatch_log_group`
- `aws_cloudtrail`

*Note: Any other resource present in the HCL file is completely ignored by the engine and will silently pass compliance checks.*
