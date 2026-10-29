# Semantic Feature: count (PASS)
resource "aws_cloudwatch_log_group" "services" {
  count             = 2
  name              = "audit-log-${count.index}"
  retention_in_days = 180
}
