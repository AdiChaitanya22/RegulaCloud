# Semantic Feature: conditional (PASS)
variable "is_production" {
  type    = bool
  default = true
}

resource "aws_cloudwatch_log_group" "audit" {
  name              = "audit-logs"
  retention_in_days = var.is_production ? 180 : 30
}
