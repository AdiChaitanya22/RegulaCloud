# Target: CTRL-AWS-LOG-180D (FAIL)
resource "aws_cloudwatch_log_group" "audit_logs" {
  name              = "system-audit-logs"
  retention_in_days = 30
}
