# Terraform Native Support Matrix

With the introduction of the Phase 5B Native Terraform pipeline (`terraform_cli.py`), RegulaCloud now processes native Terraform execution plans (`terraform show -json`). The following Terraform features are now fully resolved and evaluated via standard Rego OPA policies:

| Feature | Supported in Native Mode | Supported in Synthetic Mode |
| -------- | -------- | -------- |
| Base Resource Attributes | ✅ Yes | ✅ Yes |
| Complex Nested Blocks | ✅ Yes | ❌ Partial (Regex bugs) |
| Variables (`var.xyz`) | ✅ Yes | ❌ No |
| Locals (`local.xyz`) | ✅ Yes | ❌ No |
| Meta-arguments (`count`) | ✅ Yes (Resolved) | ❌ No |
| Meta-arguments (`for_each`) | ✅ Yes (Resolved) | ❌ No |
| Local Modules | ✅ Yes (Child module recursion) | ❌ No |
| Dynamic Blocks | ✅ Yes | ❌ No |

By shifting from synthetic AST/Regex parsing to Native Terraform plans, RegulaCloud leverages Terraform's core engine to compute variables, loops, dynamic logic, and external module calls *before* validating the infrastructure against compliance constraints.
